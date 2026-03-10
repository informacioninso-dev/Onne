import csv
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django_tenants.utils import schema_context

from clinical.models import DiagnosisCatalogEntry, DiagnosisCodingSystem
from tenants.models import Client


HEADER_ALIASES = {
    'code': {'code', 'codigo', 'cie10', 'cie-10', 'icd10', 'icd-10', 'diagnosiscode', 'diagcode'},
    'title': {'title', 'name', 'description', 'descripcion', 'diagnostico', 'diagnosis'},
}

XML_NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'rel': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pkgrel': 'http://schemas.openxmlformats.org/package/2006/relationships',
}


def normalize_header(value):
    return ''.join(char for char in (value or '').strip().lower() if char.isalnum())


def resolve_header(headers, explicit_name, aliases):
    if explicit_name:
        for header in headers:
            if header == explicit_name:
                return header
        raise CommandError(f"No existe la columna '{explicit_name}' en el archivo.")

    for header in headers:
        if normalize_header(header) in aliases:
            return header
    raise CommandError('No se pudieron detectar automaticamente las columnas de codigo y descripcion.')


def column_index(cell_ref):
    letters = []
    for char in cell_ref:
        if char.isalpha():
            letters.append(char.upper())
        else:
            break

    index = 0
    for char in letters:
        index = (index * 26) + (ord(char) - ord('A') + 1)
    return max(index - 1, 0)


def xlsx_cell_value(cell, shared_strings):
    cell_type = cell.attrib.get('t')
    if cell_type == 'inlineStr':
        return ''.join(node.text or '' for node in cell.findall('main:is/main:t', XML_NS))

    raw_value = cell.findtext('main:v', default='', namespaces=XML_NS)
    if cell_type == 's' and raw_value != '':
        return shared_strings[int(raw_value)]
    if cell_type == 'b':
        return 'TRUE' if raw_value == '1' else 'FALSE'
    return raw_value or ''


def load_shared_strings(zip_file):
    if 'xl/sharedStrings.xml' not in zip_file.namelist():
        return []

    root = ElementTree.fromstring(zip_file.read('xl/sharedStrings.xml'))
    values = []
    for item in root.findall('main:si', XML_NS):
        values.append(''.join(node.text or '' for node in item.iterfind('.//main:t', XML_NS)))
    return values


def resolve_worksheet_path(zip_file, sheet_name=None):
    workbook = ElementTree.fromstring(zip_file.read('xl/workbook.xml'))
    rels = ElementTree.fromstring(zip_file.read('xl/_rels/workbook.xml.rels'))
    rel_map = {rel.attrib['Id']: rel.attrib['Target'] for rel in rels.findall('pkgrel:Relationship', XML_NS)}

    sheets = workbook.findall('main:sheets/main:sheet', XML_NS)
    if not sheets:
        raise CommandError('El archivo XLSX no contiene hojas.')

    selected_sheet = None
    if sheet_name:
        for sheet in sheets:
            if sheet.attrib.get('name') == sheet_name:
                selected_sheet = sheet
                break
        if selected_sheet is None:
            raise CommandError(f"No existe la hoja '{sheet_name}' en el archivo XLSX.")
    else:
        selected_sheet = sheets[0]

    relationship_id = selected_sheet.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    target = rel_map.get(relationship_id)
    if not target:
        raise CommandError('No se pudo resolver la hoja seleccionada dentro del XLSX.')
    return target if target.startswith('xl/') else f"xl/{target.lstrip('/')}"


def load_xlsx_rows(file_path, sheet_name=None):
    try:
        with ZipFile(file_path) as zip_file:
            shared_strings = load_shared_strings(zip_file)
            worksheet_path = resolve_worksheet_path(zip_file, sheet_name=sheet_name)
            worksheet = ElementTree.fromstring(zip_file.read(worksheet_path))
    except BadZipFile as exc:
        raise CommandError(f"El archivo '{file_path}' no es un XLSX valido.") from exc

    rows = []
    for row in worksheet.findall('.//main:sheetData/main:row', XML_NS):
        values = []
        current_index = 0
        for cell in row.findall('main:c', XML_NS):
            target_index = column_index(cell.attrib.get('r', 'A1'))
            while current_index < target_index:
                values.append('')
                current_index += 1
            values.append(xlsx_cell_value(cell, shared_strings))
            current_index += 1
        rows.append(values)
    return rows


def load_csv_rows(file_path):
    with open(file_path, 'r', encoding='utf-8-sig', newline='') as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;|\t')
        except csv.Error:
            dialect = csv.excel
        return list(csv.reader(handle, dialect))


class Command(BaseCommand):
    help = 'Importar catalogo CIE-10 desde CSV o XLSX hacia uno o varios tenants.'

    def add_arguments(self, parser):
        parser.add_argument('file_path')
        parser.add_argument('--sheet', dest='sheet_name')
        parser.add_argument('--schema', action='append', dest='schemas')
        parser.add_argument('--all-tenants', action='store_true', dest='all_tenants')
        parser.add_argument('--code-column', dest='code_column')
        parser.add_argument('--title-column', dest='title_column')

    def handle(self, *args, **options):
        file_path = Path(options['file_path']).expanduser()
        if not file_path.exists():
            raise CommandError(f"No existe el archivo '{file_path}'.")

        rows = self._load_rows(file_path, options.get('sheet_name'))
        if not rows:
            raise CommandError('El archivo no contiene filas para importar.')

        headers = [str(value).strip() for value in rows[0]]
        if not any(headers):
            raise CommandError('La primera fila debe contener encabezados.')

        code_header = resolve_header(headers, options.get('code_column'), HEADER_ALIASES['code'])
        title_header = resolve_header(headers, options.get('title_column'), HEADER_ALIASES['title'])
        header_map = {header: index for index, header in enumerate(headers)}
        normalized_rows = self._normalize_rows(rows[1:], header_map[code_header], header_map[title_header])
        if not normalized_rows:
            raise CommandError('No se encontraron filas validas con codigo y descripcion.')

        for schema_name in self._resolve_target_schemas(options):
            with schema_context(schema_name):
                created, updated = self._import_rows(normalized_rows)
            self.stdout.write(self.style.SUCCESS(f'{schema_name}: {created} creados, {updated} actualizados.'))

    def _load_rows(self, file_path, sheet_name=None):
        if file_path.suffix.lower() == '.csv':
            return load_csv_rows(file_path)
        if file_path.suffix.lower() == '.xlsx':
            return load_xlsx_rows(file_path, sheet_name=sheet_name)
        raise CommandError('Formato no soportado. Usa CSV o XLSX.')

    def _normalize_rows(self, rows, code_index, title_index):
        normalized = []
        for row in rows:
            code = str(row[code_index]).strip().upper() if len(row) > code_index else ''
            title = str(row[title_index]).strip() if len(row) > title_index else ''
            if code and title:
                normalized.append((code, title))
        return normalized

    def _resolve_target_schemas(self, options):
        if options.get('all_tenants'):
            schemas = list(Client.objects.filter(is_active=True).values_list('schema_name', flat=True))
            if not schemas:
                raise CommandError('No existen tenants activos para importar.')
            return schemas

        explicit_schemas = options.get('schemas') or []
        if explicit_schemas:
            found = list(Client.objects.filter(schema_name__in=explicit_schemas).values_list('schema_name', flat=True))
            missing = sorted(set(explicit_schemas) - set(found))
            if missing:
                raise CommandError(f"No existen los schemas: {', '.join(missing)}")
            return found

        current_schema = connection.schema_name
        if current_schema and current_schema != 'public':
            return [current_schema]
        raise CommandError('Debes indicar --schema o --all-tenants al importar CIE-10 desde consola.')

    @transaction.atomic
    def _import_rows(self, rows):
        created = 0
        updated = 0
        for code, title in rows:
            _, was_created = DiagnosisCatalogEntry.objects.update_or_create(
                system=DiagnosisCodingSystem.CIE10,
                code=code,
                defaults={'title': title, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return created, updated

import pytest

from django.db import connection
from django.conf import settings

from baserow.core.exceptions import UserNotInGroupError
from baserow.contrib.database.table.models import Table
from baserow.contrib.database.table.handler import TableHandler
from baserow.contrib.database.table.exceptions import (
    TableDoesNotExist, InvalidInitialTableData, InitialTableDataLimitExceeded
)
from baserow.contrib.database.fields.models import (
    TextField, LongTextField, BooleanField
)
from baserow.contrib.database.views.models import GridView, GridViewFieldOptions


@pytest.mark.django_db
def test_get_database_table(data_fixture):
    user = data_fixture.create_user()
    table = data_fixture.create_database_table(user=user)
    table_2 = data_fixture.create_database_table()
    handler = TableHandler()

    with pytest.raises(UserNotInGroupError):
        handler.get_table(user=user, table_id=table_2.id)

    with pytest.raises(TableDoesNotExist):
        handler.get_table(user=user, table_id=99999)

    # If the error is raised we know for sure that the base query has resolved.
    with pytest.raises(AttributeError):
        handler.get_table(
            user=user,
            table_id=table.id,
            base_queryset=Table.objects.prefetch_related('UNKNOWN')
        )

    table_copy = handler.get_table(user=user, table_id=table.id)
    assert table_copy.id == table.id


@pytest.mark.django_db
def test_create_database_table(data_fixture):
    user = data_fixture.create_user()
    user_2 = data_fixture.create_user()
    database = data_fixture.create_database_application(user=user)

    handler = TableHandler()
    handler.create_table(user=user, database=database, name='Test table')

    assert Table.objects.all().count() == 1
    assert TextField.objects.all().count() == 1

    table = Table.objects.all().first()
    assert table.name == 'Test table'
    assert table.order == 1
    assert table.database == database

    primary_field = TextField.objects.all().first()
    assert primary_field.table == table
    assert primary_field.primary
    assert primary_field.name == 'Name'

    with pytest.raises(UserNotInGroupError):
        handler.create_table(user=user_2, database=database, name='')

    assert f'database_table_{table.id}' in connection.introspection.table_names()

    model = table.get_model(attribute_names=True)
    row = model.objects.create(name='Test')
    assert row.name == 'Test'

    with pytest.raises(TypeError):
        model.objects.create(does_not_exists=True)

    assert model.objects.count() == 1
    row = model.objects.get(id=row.id)
    assert row.name == 'Test'


@pytest.mark.django_db
def test_fill_example_table_data(data_fixture):
    user = data_fixture.create_user()
    database = data_fixture.create_database_application(user=user)

    table_handler = TableHandler()
    table_handler.create_table(user, database, fill_example=True, name='Table 1')

    assert Table.objects.all().count() == 1
    assert GridView.objects.all().count() == 1
    assert TextField.objects.all().count() == 1
    assert LongTextField.objects.all().count() == 1
    assert BooleanField.objects.all().count() == 1
    assert GridViewFieldOptions.objects.all().count() == 2


@pytest.mark.django_db
def test_fill_table_with_initial_data(data_fixture):
    user = data_fixture.create_user()
    database = data_fixture.create_database_application(user=user)

    table_handler = TableHandler()

    with pytest.raises(InvalidInitialTableData):
        table_handler.create_table(user, database, name='Table 1', data=[])

    with pytest.raises(InvalidInitialTableData):
        table_handler.create_table(user, database, name='Table 1', data=[[]])

    limit = settings.INITIAL_TABLE_DATA_LIMIT
    settings.INITIAL_TABLE_DATA_LIMIT = 2

    with pytest.raises(InitialTableDataLimitExceeded):
        table_handler.create_table(user, database, name='Table 1', data=[[], [], []])

    settings.INITIAL_TABLE_DATA_LIMIT = limit

    data = [
        ['A', 'B', 'C', 'D'],
        ['1-1', '1-2', '1-3', '1-4', '1-5'],
        ['2-1', '2-2', '2-3'],
        ['3-1', '3-2'],
    ]
    table = table_handler.create_table(user, database, name='Table 1', data=data,
                                       first_row_header=True)

    text_fields = TextField.objects.filter(table=table)
    assert text_fields[0].name == 'A'
    assert text_fields[1].name == 'B'
    assert text_fields[2].name == 'C'
    assert text_fields[3].name == 'D'
    assert text_fields[4].name == 'Field 5'

    assert GridView.objects.all().count() == 1

    model = table.get_model()
    results = model.objects.all()

    assert getattr(results[0], f'field_{text_fields[0].id}') == '1-1'
    assert getattr(results[0], f'field_{text_fields[1].id}') == '1-2'
    assert getattr(results[0], f'field_{text_fields[2].id}') == '1-3'
    assert getattr(results[0], f'field_{text_fields[3].id}') == '1-4'
    assert getattr(results[0], f'field_{text_fields[4].id}') == '1-5'

    assert getattr(results[1], f'field_{text_fields[0].id}') == '2-1'
    assert getattr(results[1], f'field_{text_fields[1].id}') == '2-2'
    assert getattr(results[1], f'field_{text_fields[2].id}') == '2-3'
    assert getattr(results[1], f'field_{text_fields[3].id}') == ''
    assert getattr(results[1], f'field_{text_fields[4].id}') == ''

    assert getattr(results[2], f'field_{text_fields[0].id}') == '3-1'
    assert getattr(results[2], f'field_{text_fields[1].id}') == '3-2'
    assert getattr(results[2], f'field_{text_fields[2].id}') == ''
    assert getattr(results[2], f'field_{text_fields[3].id}') == ''
    assert getattr(results[2], f'field_{text_fields[4].id}') == ''

    data = [
        ['1-1'],
        ['2-1', '2-2', '2-3'],
        ['3-1', '3-2'],
    ]
    table = table_handler.create_table(user, database, name='Table 2', data=data,
                                       first_row_header=False)

    text_fields = TextField.objects.filter(table=table)
    assert text_fields[0].name == 'Field 1'
    assert text_fields[1].name == 'Field 2'
    assert text_fields[2].name == 'Field 3'

    assert GridView.objects.all().count() == 2

    model = table.get_model()
    results = model.objects.all()

    assert getattr(results[0], f'field_{text_fields[0].id}') == '1-1'
    assert getattr(results[0], f'field_{text_fields[1].id}') == ''
    assert getattr(results[0], f'field_{text_fields[2].id}') == ''

    assert getattr(results[1], f'field_{text_fields[0].id}') == '2-1'
    assert getattr(results[1], f'field_{text_fields[1].id}') == '2-2'
    assert getattr(results[1], f'field_{text_fields[2].id}') == '2-3'

    assert getattr(results[2], f'field_{text_fields[0].id}') == '3-1'
    assert getattr(results[2], f'field_{text_fields[1].id}') == '3-2'


@pytest.mark.django_db
def test_update_database_table(data_fixture):
    user = data_fixture.create_user()
    user_2 = data_fixture.create_user()
    group = data_fixture.create_group(user=user)
    database = data_fixture.create_database_application(group=group)
    table = data_fixture.create_database_table(database=database)

    handler = TableHandler()

    with pytest.raises(UserNotInGroupError):
        handler.update_table(user=user_2, table=table, name='Test 1')

    handler.update_table(user=user, table=table, name='Test 1')

    table.refresh_from_db()

    assert table.name == 'Test 1'


@pytest.mark.django_db
def test_delete_database_table(data_fixture):
    user = data_fixture.create_user()
    user_2 = data_fixture.create_user()
    group = data_fixture.create_group(user=user)
    database = data_fixture.create_database_application(group=group)
    table = data_fixture.create_database_table(user=user, database=database)

    handler = TableHandler()

    with pytest.raises(UserNotInGroupError):
        handler.delete_table(user=user_2, table=table)

    assert Table.objects.all().count() == 1
    assert f'database_table_{table.id}' in connection.introspection.table_names()

    handler.delete_table(user=user, table=table)

    assert Table.objects.all().count() == 0
    assert f'database_table_{table.id}' not in connection.introspection.table_names()

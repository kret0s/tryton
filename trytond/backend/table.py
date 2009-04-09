#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.


class TableHandlerInterface(object):
    '''
    Define generic interface to handle database table
    '''

    def __init__(self, cursor, model, module_name=None, history=False):
        '''
        :param cursor: the database cursor
        :param model: the Model linked to the table
        :param module_name: the module name
        :param history: a boolean to define if it is a history table
        '''
        super(TableHandlerInterface, self).__init__()
        self.cursor = cursor
        if history:
            self.table_name = model._table + '__history'
        else:
            self.table_name = model._table
        self.object_name = model._name
        if history:
            self.sequence_name = self.table_name + '___id_seq'
        else:
            self.sequence_name = model._sequence
        self.module_name = module_name
        self.history = history

    @staticmethod
    def table_exist(cursor, table_name):
        '''
        Table exist

        :param cursor: the database cursor
        :param table_name: the table name
        :return: a boolean
        '''
        raise

    @staticmethod
    def table_rename(cursor, old_name, new_name):
        '''
        Rename table

        :param cursor: the database cursor
        :param old_name: the old table name
        :param new_name: the new table name
        '''
        raise

    @staticmethod
    def sequence_exist(cursor, sequence_name):
        '''
        Sequence exist

        :param cursor: the database cursor
        :param sequence_name: the sequence name
        :return: a boolean
        '''
        raise

    @staticmethod
    def sequence_rename(cursor, old_name, new_name):
        '''
        Rename sequence

        :param cursor: the database cursor
        :param old_name: the old sequence name
        :param new_name: the new sequence name
        '''
        raise

    def column_exist(self, column_name):
        '''
        Column exist

        :param column_name: the column name
        :return: a boolean
        '''
        raise

    def alter_size(self, column_name, column_type):
        '''
        Modify size of a column

        :param column_name: the column name
        :param column_type: the column definition
        '''
        raise

    def alter_type(self, column_name, column_type):
        '''
        Modify type of a column

        :param column_name: the column name
        :param column_type: the column definition
        '''
        raise

    def db_default(self, column_name, value):
        '''
        Set a default on a column

        :param column_name: the column name
        :param value: the default value
        '''
        raise

    def add_raw_column(self, column_name, column_type, column_format,
            default_fun=None, field_size=None, migrate=True):
        '''
        Add a column

        :param column_name: the column name
        :param column_type: the column definition
        :param column_format: the function to format default value
        :param default_fun: the function that return the default value
        :param field_size: the size of the column if there is one
        :param migrate: boolean to try to migrate the column if exists
        '''
        raise

    def add_fk(self, column_name, reference, on_delete=None):
        '''
        Add a foreign key

        :param column_name: the column name
        :param reference: the foreign table name
        :param on_delete: the "on delete" value
        '''
        raise

    def index_action(self, column_name, action='add'):
        '''
        Add/remove an index

        :param column_name: the column name or a list of column name
        :param action: 'add' or 'remove'
        '''
        raise

    def not_null_action(self, column_name, action='add'):
        '''
        Add/remove a "not null"

        :param column_name: the column name
        :param action: 'add' or 'remove'
        '''
        raise

    def add_constraint(self, ident, constraint, exception=False):
        '''
        Add a constraint

        :param ident: the name of the constraint
        :param constraint: the definition of the constraint
        :param exception: a boolean to raise or not an exception
            if it is not possible to add the constraint
        '''
        raise

    def drop_constraint(self, ident, exception=False):
        '''
        Remove a constraint

        :param ident: the name of the constraint
        :param exception: a boolean to raise or not an exception
            if it is not possible to remove the constraint
        '''
        raise

    def drop_column(self, column_name, exception=False):
        '''
        Remove a column

        :param column_name: the column name
        :param exception: a boolean to raise or not an exception
            if it is not possible to remove the column
        '''
        raise

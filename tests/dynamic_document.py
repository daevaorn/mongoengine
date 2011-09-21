import unittest

from mongoengine import *
from mongoengine.connection import _get_db

class DynamicDocTest(unittest.TestCase):

    def setUp(self):
        connect(db='mongoenginetest')
        self.db = _get_db()

        class Person(DynamicDocument):
            name = StringField()

        Person.drop_collection()

        self.Person = Person

    def test_simple_dynamic_document(self):
        """Ensures simple dynamic documents are saved correctly"""

        p = self.Person()
        p.name = "James"
        p.age = 34

        self.assertEquals(p.to_mongo(),
            {"_types": ["Person"], "_cls": "Person",
             "name": "James", "age": 34}
        )

        p.save()

        self.assertEquals(self.Person.objects.first().age, 34)

        # Confirm no changes to self.Person
        self.assertFalse(hasattr(self.Person, 'age'))

    def test_change_scope_of_variable(self):
        """Test changing the scope of a dynamic field has no adverse effects"""
        p = self.Person()
        p.name = "Dean"
        p.misc = 22
        p.save()

        p = self.Person.objects.get()
        p.misc = {'hello': 'world'}
        p.save()

        p = self.Person.objects.get()
        self.assertEquals(p.misc, {'hello': 'world'})

    def test_dynamic_document_queries(self):
        """Ensure we can query dynamic fields"""
        p = self.Person()
        p.name = "Dean"
        p.age = 22
        p.save()

        self.assertEquals(1, self.Person.objects(age=22).count())
        p = self.Person.objects(age=22)
        p = p.get()
        self.assertEquals(22, p.age)

    def test_complex_data_lookups(self):
        """Ensure you can query dynamic document dynamic fields"""
        p = self.Person()
        p.misc = {'hello': 'world'}
        p.save()

        self.assertEquals(1, self.Person.objects(misc__hello='world').count())

    def test_inheritance(self):
        """Ensure that dynamic document plays nice with inheritance"""
        class Employee(self.Person):
            salary = IntField()

        Employee.drop_collection()

        self.assertTrue('name' in Employee._fields)
        self.assertTrue('salary' in Employee._fields)
        self.assertEqual(Employee._get_collection_name(),
                         self.Person._get_collection_name())

        joe_bloggs = Employee()
        joe_bloggs.name = "Joe Bloggs"
        joe_bloggs.salary = 10
        joe_bloggs.age = 20
        joe_bloggs.save()

        self.assertEquals(1, self.Person.objects(age=20).count())
        self.assertEquals(1, Employee.objects(age=20).count())

        joe_bloggs = self.Person.objects.first()
        self.assertTrue(isinstance(joe_bloggs, Employee))

    def test_embedded_dynamic_document(self):
        """Test dynamic embedded documents"""
        class Embedded(DynamicEmbeddedDocument):
            pass

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()

        embedded_1 = Embedded()
        embedded_1.string_field = 'hello'
        embedded_1.int_field = 1
        embedded_1.dict_field = {'hello': 'world'}
        embedded_1.list_field = ['1', 2, {'hello': 'world'}]
        doc.embedded_field = embedded_1

        self.assertEquals(doc.to_mongo(), {"_types": ['Doc'], "_cls": "Doc",
            "embedded_field": {
                "_types": ['Embedded'], "_cls": "Embedded",
                "string_field": "hello",
                "int_field": 1,
                "dict_field": {"hello": "world"},
                "list_field": ['1', 2, {'hello': 'world'}]
            }
        })
        doc.save()

        doc = Doc.objects.first()
        self.assertEquals(doc.embedded_field.__class__, Embedded)
        self.assertEquals(doc.embedded_field.string_field, "hello")
        self.assertEquals(doc.embedded_field.int_field, 1)
        self.assertEquals(doc.embedded_field.dict_field, {'hello': 'world'})
        self.assertEquals(doc.embedded_field.list_field, ['1', 2, {'hello': 'world'}])

    def test_complex_embedded_documents(self):
        """Test complex dynamic embedded documents setups"""
        class Embedded(DynamicEmbeddedDocument):
            pass

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()

        embedded_1 = Embedded()
        embedded_1.string_field = 'hello'
        embedded_1.int_field = 1
        embedded_1.dict_field = {'hello': 'world'}

        embedded_2 = Embedded()
        embedded_2.string_field = 'hello'
        embedded_2.int_field = 1
        embedded_2.dict_field = {'hello': 'world'}
        embedded_2.list_field = ['1', 2, {'hello': 'world'}]

        embedded_1.list_field = ['1', 2, embedded_2]
        doc.embedded_field = embedded_1

        self.assertEquals(doc.to_mongo(), {"_types": ['Doc'], "_cls": "Doc",
            "embedded_field": {
                "_types": ['Embedded'], "_cls": "Embedded",
                "string_field": "hello",
                "int_field": 1,
                "dict_field": {"hello": "world"},
                "list_field": ['1', 2,
                    {"_types": ['Embedded'], "_cls": "Embedded",
                    "string_field": "hello",
                    "int_field": 1,
                    "dict_field": {"hello": "world"},
                    "list_field": ['1', 2, {'hello': 'world'}]}
                ]
            }
        })
        doc.save()
        doc = Doc.objects.first()
        self.assertEquals(doc.embedded_field.__class__, Embedded)
        self.assertEquals(doc.embedded_field.string_field, "hello")
        self.assertEquals(doc.embedded_field.int_field, 1)
        self.assertEquals(doc.embedded_field.dict_field, {'hello': 'world'})
        self.assertEquals(doc.embedded_field.list_field[0], '1')
        self.assertEquals(doc.embedded_field.list_field[1], 2)

        embedded_field = doc.embedded_field.list_field[2]

        self.assertEquals(embedded_field.__class__, Embedded)
        self.assertEquals(embedded_field.string_field, "hello")
        self.assertEquals(embedded_field.int_field, 1)
        self.assertEquals(embedded_field.dict_field, {'hello': 'world'})
        self.assertEquals(embedded_field.list_field, ['1', 2, {'hello': 'world'}])

    def test_delta_for_dynamic_documents(self):
        p = self.Person()
        p.name = "Dean"
        p.age = 22
        p.save()

        p.age = 24
        self.assertEquals(p.age, 24)
        self.assertEquals(p._get_changed_fields(), ['age'])
        self.assertEquals(p._delta(), ({'age': 24}, {}))

        p = self.Person.objects(age=22).get()
        p.age = 24
        self.assertEquals(p.age, 24)
        self.assertEquals(p._get_changed_fields(), ['age'])
        self.assertEquals(p._delta(), ({'age': 24}, {}))

        p.save()
        self.assertEquals(1, self.Person.objects(age=24).count())

    def test_delta(self):

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()
        doc.save()

        doc = Doc.objects.first()
        self.assertEquals(doc._get_changed_fields(), [])
        self.assertEquals(doc._delta(), ({}, {}))

        doc.string_field = 'hello'
        self.assertEquals(doc._get_changed_fields(), ['string_field'])
        self.assertEquals(doc._delta(), ({'string_field': 'hello'}, {}))

        doc._changed_fields = []
        doc.int_field = 1
        self.assertEquals(doc._get_changed_fields(), ['int_field'])
        self.assertEquals(doc._delta(), ({'int_field': 1}, {}))

        doc._changed_fields = []
        dict_value = {'hello': 'world', 'ping': 'pong'}
        doc.dict_field = dict_value
        self.assertEquals(doc._get_changed_fields(), ['dict_field'])
        self.assertEquals(doc._delta(), ({'dict_field': dict_value}, {}))

        doc._changed_fields = []
        list_value = ['1', 2, {'hello': 'world'}]
        doc.list_field = list_value
        self.assertEquals(doc._get_changed_fields(), ['list_field'])
        self.assertEquals(doc._delta(), ({'list_field': list_value}, {}))

        # Test unsetting
        doc._changed_fields = []
        doc.dict_field = {}
        self.assertEquals(doc._get_changed_fields(), ['dict_field'])
        self.assertEquals(doc._delta(), ({}, {'dict_field': 1}))

        doc._changed_fields = []
        doc.list_field = []
        self.assertEquals(doc._get_changed_fields(), ['list_field'])
        self.assertEquals(doc._delta(), ({}, {'list_field': 1}))

    def test_delta_recursive(self):
        """Testing deltaing works with dynamic documents"""
        class Embedded(DynamicEmbeddedDocument):
            pass

        class Doc(DynamicDocument):
            pass

        Doc.drop_collection()
        doc = Doc()
        doc.save()

        doc = Doc.objects.first()
        self.assertEquals(doc._get_changed_fields(), [])
        self.assertEquals(doc._delta(), ({}, {}))

        embedded_1 = Embedded()
        embedded_1.string_field = 'hello'
        embedded_1.int_field = 1
        embedded_1.dict_field = {'hello': 'world'}
        embedded_1.list_field = ['1', 2, {'hello': 'world'}]
        doc.embedded_field = embedded_1

        self.assertEquals(doc._get_changed_fields(), ['embedded_field'])

        embedded_delta = {
            '_types': ['Embedded'],
            '_cls': 'Embedded',
            'string_field': 'hello',
            'int_field': 1,
            'dict_field': {'hello': 'world'},
            'list_field': ['1', 2, {'hello': 'world'}]
        }
        self.assertEquals(doc.embedded_field._delta(), (embedded_delta, {}))
        self.assertEquals(doc._delta(), ({'embedded_field': embedded_delta}, {}))

        doc.save()
        doc.reload()

        doc.embedded_field.dict_field = {}
        self.assertEquals(doc._get_changed_fields(), ['embedded_field.dict_field'])
        self.assertEquals(doc.embedded_field._delta(), ({}, {'dict_field': 1}))

        self.assertEquals(doc._delta(), ({}, {'embedded_field.dict_field': 1}))
        doc.save()
        doc.reload()

        doc.embedded_field.list_field = []
        self.assertEquals(doc._get_changed_fields(), ['embedded_field.list_field'])
        self.assertEquals(doc.embedded_field._delta(), ({}, {'list_field': 1}))
        self.assertEquals(doc._delta(), ({}, {'embedded_field.list_field': 1}))
        doc.save()
        doc.reload()

        embedded_2 = Embedded()
        embedded_2.string_field = 'hello'
        embedded_2.int_field = 1
        embedded_2.dict_field = {'hello': 'world'}
        embedded_2.list_field = ['1', 2, {'hello': 'world'}]

        doc.embedded_field.list_field = ['1', 2, embedded_2]
        self.assertEquals(doc._get_changed_fields(), ['embedded_field.list_field'])
        self.assertEquals(doc.embedded_field._delta(), ({
            'list_field': ['1', 2, {
                '_cls': 'Embedded',
                '_types': ['Embedded'],
                'string_field': 'hello',
                'dict_field': {'hello': 'world'},
                'int_field': 1,
                'list_field': ['1', 2, {'hello': 'world'}],
            }]
        }, {}))

        self.assertEquals(doc._delta(), ({
            'embedded_field.list_field': ['1', 2, {
                '_cls': 'Embedded',
                 '_types': ['Embedded'],
                 'string_field': 'hello',
                 'dict_field': {'hello': 'world'},
                 'int_field': 1,
                 'list_field': ['1', 2, {'hello': 'world'}],
            }]
        }, {}))
        doc.save()
        doc.reload()

        self.assertEquals(doc.embedded_field.list_field[2]._changed_fields, [])
        self.assertEquals(doc.embedded_field.list_field[0], '1')
        self.assertEquals(doc.embedded_field.list_field[1], 2)
        for k in doc.embedded_field.list_field[2]._fields:
            self.assertEquals(doc.embedded_field.list_field[2][k], embedded_2[k])

        doc.embedded_field.list_field[2].string_field = 'world'
        self.assertEquals(doc._get_changed_fields(), ['embedded_field.list_field.2.string_field'])
        self.assertEquals(doc.embedded_field._delta(), ({'list_field.2.string_field': 'world'}, {}))
        self.assertEquals(doc._delta(), ({'embedded_field.list_field.2.string_field': 'world'}, {}))
        doc.save()
        doc.reload()
        self.assertEquals(doc.embedded_field.list_field[2].string_field, 'world')

        # Test multiple assignments
        doc.embedded_field.list_field[2].string_field = 'hello world'
        doc.embedded_field.list_field[2] = doc.embedded_field.list_field[2]
        self.assertEquals(doc._get_changed_fields(), ['embedded_field.list_field'])
        self.assertEquals(doc.embedded_field._delta(), ({
            'list_field': ['1', 2, {
            '_types': ['Embedded'],
            '_cls': 'Embedded',
            'string_field': 'hello world',
            'int_field': 1,
            'list_field': ['1', 2, {'hello': 'world'}],
            'dict_field': {'hello': 'world'}}]}, {}))
        self.assertEquals(doc._delta(), ({
            'embedded_field.list_field': ['1', 2, {
                '_types': ['Embedded'],
                '_cls': 'Embedded',
                'string_field': 'hello world',
                'int_field': 1,
                'list_field': ['1', 2, {'hello': 'world'}],
                'dict_field': {'hello': 'world'}}
            ]}, {}))
        doc.save()
        doc.reload()
        self.assertEquals(doc.embedded_field.list_field[2].string_field, 'hello world')

        # Test list native methods
        doc.embedded_field.list_field[2].list_field.pop(0)
        self.assertEquals(doc._delta(), ({'embedded_field.list_field.2.list_field': [2, {'hello': 'world'}]}, {}))
        doc.save()
        doc.reload()

        doc.embedded_field.list_field[2].list_field.append(1)
        self.assertEquals(doc._delta(), ({'embedded_field.list_field.2.list_field': [2, {'hello': 'world'}, 1]}, {}))
        doc.save()
        doc.reload()
        self.assertEquals(doc.embedded_field.list_field[2].list_field, [2, {'hello': 'world'}, 1])

        doc.embedded_field.list_field[2].list_field.sort()
        doc.save()
        doc.reload()
        self.assertEquals(doc.embedded_field.list_field[2].list_field, [1, 2, {'hello': 'world'}])

        del(doc.embedded_field.list_field[2].list_field[2]['hello'])
        self.assertEquals(doc._delta(), ({'embedded_field.list_field.2.list_field': [1, 2, {}]}, {}))
        doc.save()
        doc.reload()

        del(doc.embedded_field.list_field[2].list_field)
        self.assertEquals(doc._delta(), ({}, {'embedded_field.list_field.2.list_field': 1}))

        doc.save()
        doc.reload()

        doc.dict_field = {'embedded': embedded_1}
        doc.save()
        doc.reload()

        doc.dict_field['embedded'].string_field = 'Hello World'
        self.assertEquals(doc._get_changed_fields(), ['dict_field.embedded.string_field'])
        self.assertEquals(doc._delta(), ({'dict_field.embedded.string_field': 'Hello World'}, {}))

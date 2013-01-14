import kimobjects

pr = kimobjects.Property('PR_000000000001_000')
pm = kimobjects.Primitive('schema_pr')

from jsonschema import validate
import simplejson

CREATE TABLE dependency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id INTEGER,
    parent_id INTEGER,
    FOREIGN KEY(child_id) REFERENCES object(id),
    FOREIGN KEY(parent_id) REFERENCES object(id)
);
CREATE TABLE match (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    runner_id INTEGER,
    subject_id INTEGER,
    FOREIGN KEY(runner_id) REFERENCES object(id),
    FOREIGN KEY(subject_id) REFERENCES object(id)
);
CREATE TABLE object (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kimcode TEXT UNIQUE,
    kimid TEXT,
    name TEXT,
    leader TEXT,
    number INTEGER,
    version INTEGER
);
CREATE TABLE object_stuff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id INTEGER,
    key TEXT,
    value TEXT,
    FOREIGN KEY(object_id) REFERENCES object(id)
);
CREATE TABLE property (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    blob BLOB
);
CREATE TABLE property_stuff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER,
    key TEXT,
    value TEXT,
    FOREIGN KEY(property_id) REFERENCES property(id)
);
CREATE TABLE result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    runner_id INTEGER,
    subject_id INTEGER,
    uuid TEXT UNIQUE,
    kind TEXT,
    FOREIGN KEY(runner_id) REFERENCES object(id),
    FOREIGN KEY(subject_id) REFERENCES object(id)
);
CREATE TABLE result_property (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER,
    property_id INTEGER,
    FOREIGN KEY(result_id) REFERENCES result(id),
    FOREIGN KEY(property_id) REFERENCES property(id)
);
CREATE VIEW errorresult AS SELECT * from result WHERE result.kind = 'er';
CREATE VIEW full AS SELECT property.id as property_id, property.name as property_name, property.blob as blob, property_stuff.key as key, property_stuff.value as value, result.id as result_id, result.uuid as result_uuid, runner.id as runner_id, runner.kimcode as runner_kimcode, subject.id as subject_id, subject.kimcode as subject_kimcode, test_testdriver.testdriver_id as testdriver_id, test_testdriver.testdriver_kimcode as testdriver_kimcode, model_modeldriver.modeldriver_id as modeldriver_id, model_modeldriver.modeldriver_kimcode as modeldriver_kimcode FROM property_stuff LEFT JOIN property ON property.id = property_stuff.property_id LEFT JOIN result_property ON result_property.property_id = property.id LEFT JOIN result ON result.id = result_property.result_id LEFT JOIN object as runner ON runner.id = result.runner_id LEFT JOIN object as subject ON subject.id = result.subject_id LEFT JOIN test_testdriver ON test_testdriver.test_id = result.runner_id LEFT JOIN model_modeldriver ON model_modeldriver.model_id = result.subject_id;
CREATE VIEW model AS SELECT * from object WHERE object.leader = "MO";
CREATE VIEW model_modeldriver AS SELECT model.id as model_id, model.kimcode as model_kimcode, modeldriver.id as modeldriver_id, modeldriver.kimcode as modeldriver_kimcode FROM object as model JOIN object_stuff ON object_stuff.object_id = model.id JOIN object as modeldriver ON modeldriver.kimcode = object_stuff.value WHERE object_stuff.key = "MODEL_DRIVER_NAME" AND model.leader = "MO";
CREATE VIEW modeldriver AS SELECT * from object WHERE object.leader = "MD";
CREATE VIEW runner_subject AS SELECT runner_id, subject_id, runner.kimcode as runner_kimcode, subject.kimcode as subject_kimcode, result.id as result_id, result.uuid as result_uuid FROM result JOIN object as runner ON result.runner_id = runner.id JOIN object as subject ON result.subject_id = subject.id;
CREATE VIEW runner_subject_property AS SELECT runner.id as runner_id, runner.kimcode as runner_kimcode, subject.id as subject_id, subject.kimcode AS subject_kimcode, property.id as property_id, property.name as property_name FROM object as runner JOIN test_result ON test_result.test_id = runner.id JOIN result ON result.id = test_result.result_id JOIN object as subject ON subject.id = result.subject_id JOIN result_property ON test_result.result_id = result_property.result_id JOIN property ON property.id = result_property.property_id;
CREATE VIEW runner_subject_result AS SELECT runner_subject_property.runner_id AS runner_id, runner_subject_property.runner_kimcode AS runner_kimcode, runner_subject_property.subject_id AS subject_id, runner_subject_property.subject_kimcode AS subject_kimcode, result.id as result_id, result.uuid as result_uuid FROM runner_subject_property JOIN result_property ON result_property.property_id = runner_subject_property.property_id JOIN result;
CREATE VIEW test AS SELECT * from object where object.leader = "TE";
CREATE VIEW test_model AS SELECT test.id as test_id, test.kimcode as test_kimcode, model.id as model_id, model.kimcode as model_kimcode, result.id as result_id, result.uuid as result_uuid FROM object as test JOIN result ON result.runner_id = test.id JOIN object as model ON result.subject_id = model.id;
CREATE VIEW test_result AS SELECT test.id as test_id, test.kimcode as test_kimcode, result.id as result_id, result.uuid as result_uuid FROM object as test JOIN result ON result.runner_id = test.id;
CREATE VIEW test_testdriver AS SELECT test.id as test_id, test.kimcode as test_kimcode, testdriver.id as testdriver_id, testdriver.kimcode as testdriver_kimcode FROM object as test JOIN object_stuff ON object_stuff.object_id = test.id JOIN object as testdriver ON testdriver.kimcode = object_stuff.value WHERE object_stuff.key = "TEST_DRIVER_NAME" AND test.leader = "TE";
CREATE VIEW testdriver AS SELECT * from object WHERE object.leader = "TD";
CREATE VIEW testresult AS SELECT * from result WHERE result.kind = 'tr';
CREATE VIEW verificationmodel AS SELECT * from object WHERE object.leader = "VM";
CREATE VIEW verificationresult AS SELECT * from result WHERE result.kind = 'vr';
CREATE VIEW verificationtest AS SELECT * from object WHERE object.leader = "VT";
CREATE INDEX key_idx ON property_stuff (key);
CREATE INDEX kimcode_idx ON object (kimcode);
CREATE INDEX object_id_kimcode ON object (id,kimcode);
CREATE INDEX object_stuff_idx ON object_stuff (object_id);
CREATE INDEX property_idx ON property (id);
CREATE INDEX property_name_idx ON property (name);
CREATE INDEX property_stuff_idx ON property_stuff (id);
CREATE INDEX runner_idx ON result (runner_id);
CREATE INDEX runner_subject_idx ON result (runner_id, subject_id);
CREATE INDEX subject_idx ON result (subject_id);

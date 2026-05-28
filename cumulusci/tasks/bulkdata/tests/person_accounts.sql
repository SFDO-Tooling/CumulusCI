BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "PersonContact" (
        id INTEGER NOT NULL, 
        "IsPersonAccount" VARCHAR(255), 
        "AccountId" VARCHAR(255), 
        PRIMARY KEY (id)
);
INSERT INTO PersonContact VALUES(1,'true','1');
INSERT INTO PersonContact VALUES(2,'false','0');
CREATE TABLE IF NOT EXISTS "Account" (
        id INTEGER NOT NULL, 
        "FirstName" VARCHAR(255), 
        "LastName" VARCHAR(255), 
        "PersonMailingStreet" VARCHAR(255), 
        "PersonMailingCity" VARCHAR(255), 
        "PersonMailingState" VARCHAR(255), 
        "PersonMailingCountry" VARCHAR(255), 
        "PersonMailingPostalCode" VARCHAR(255), 
        "PersonEmail" VARCHAR(255), 
        "Phone" VARCHAR(255), 
        "PersonMobilePhone" VARCHAR(255), 
        "PersonContactId" VARCHAR(255), 
        PRIMARY KEY (id)
);
INSERT INTO Account VALUES(1,'Ana','Jacobson','61034 Calderon Point','Robinview','Michigan','USA','38677','AnJacobson1997@example.com','(330)320-6522','001-377-923-2289','1');
CREATE TABLE IF NOT EXISTS "cumulusci_id_table" (
        id VARCHAR(255) NOT NULL, 
        sf_id VARCHAR(18), 
        PRIMARY KEY (id)
);
INSERT INTO cumulusci_id_table VALUES('Account-1','0016300001AKkZyAAL');
INSERT INTO cumulusci_id_table VALUES('Contact-1','0036300000wjVUBAA2');
COMMIT;

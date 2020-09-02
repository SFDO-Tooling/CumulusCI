BEGIN TRANSACTION;
CREATE TABLE contacts (
	sf_id VARCHAR(255) NOT NULL, 
	first_name VARCHAR(255), 
	last_name VARCHAR(255), 
	email VARCHAR(255), 
	household_id VARCHAR(255), 
	PRIMARY KEY (sf_id)
);
INSERT INTO "contacts" VALUES('1','Test☃','User','test@example.com','1');
INSERT INTO "contacts" VALUES('2','Error','User','error@example.com','1');
CREATE TABLE households (
	sf_id VARCHAR(255) NOT NULL, 
	record_type VARCHAR(255), 
	PRIMARY KEY (sf_id)
);
INSERT INTO "households" VALUES('1','HH_Account');
COMMIT;

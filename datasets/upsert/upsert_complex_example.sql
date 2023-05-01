BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255),
	"AccountNumber" VARCHAR(255),
	PRIMARY KEY (id)
);
CREATE TABLE "Contact" (
	id INTEGER NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Email" VARCHAR(255),
	PRIMARY KEY (id)
);
-- Change emails based on FirstName/LastName
INSERT INTO "Contact" VALUES(1,'Michael','Bluth','Nichael.Bluth@example.com');
INSERT INTO "Contact" VALUES(2,'GOB','Bluth','GeorgeOscar.Bluth@example.com');
INSERT INTO "Contact" VALUES(3,'Lindsay','Bluth','lindsay.bluth@example.com');
INSERT INTO "Contact" VALUES(4,'Annyong','Bluth','annyong.bluth@example.com');
COMMIT;

CREATE TABLE "Opportunity" (
	id INTEGER NOT NULL,
	"Name" VARCHAR(255),
	"CloseDate" VARCHAR(255),
	"Amount" VARCHAR(255),
	"StageName" VARCHAR(255),
	"AccountId" VARCHAR(255),
	"ContactId" VARCHAR(255),
	PRIMARY KEY (id)
);

INSERT INTO
	"Opportunity"
VALUES
	(
		1,
		'Illusional Opportunity',
		'2021-10-03',
		'136',
		'In Progress',
		NULL,
		'2'
	);
INSERT INTO
	"Opportunity"
VALUES
	(
		2,
		'Espionage Opportunity',
		'2021-10-03',
		'200',
		'In Progress',
		NULL,
		'4'
	);

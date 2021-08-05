BEGIN TRANSACTION;

CREATE TABLE "Account" (
	id INTEGER NOT NULL,
	"Name" VARCHAR(255),
	"Description" VARCHAR(255),
	"NumberOfEmployees" VARCHAR(255),
	"BillingStreet" VARCHAR(255),
	"BillingCity" VARCHAR(255),
	"BillingState" VARCHAR(255),
	"BillingPostalCode" VARCHAR(255),
	"BillingCountry" VARCHAR(255),
	"ShippingStreet" VARCHAR(255),
	"ShippingCity" VARCHAR(255),
	"ShippingState" VARCHAR(255),
	"ShippingPostalCode" VARCHAR(255),
	"ShippingCountry" VARCHAR(255),
	"Phone" VARCHAR(255),
	"Fax" VARCHAR(255),
	"Website" VARCHAR(255),
	"AccountNumber" VARCHAR(255),
	PRIMARY KEY (id)
);

INSERT INTO
	"Account"
VALUES
	(
		1,
		'The Bluth Company',
		'Solid as a rock',
		'6',
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL
	);

INSERT INTO
	"Account"
VALUES
	(
		2,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL
	);

CREATE TABLE "Contact" (
	id INTEGER NOT NULL,
	"FirstName" VARCHAR(255),
	"LastName" VARCHAR(255),
	"AccountId" VARCHAR(255),
	"Salutation" VARCHAR(255),
	"Email" VARCHAR(255),
	"Phone" VARCHAR(255),
	"MobilePhone" VARCHAR(255),
	"Title" VARCHAR(255),
	"Birthdate" VARCHAR(255),
	PRIMARY KEY (id)
);

INSERT INTO
	"Contact"
VALUES
	(
		1,
		'Michael',
		'Bluth',
		'1',
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL
	);

INSERT INTO
	"Contact"
VALUES
	(
		2,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL,
		NULL
	);

CREATE TABLE "Opportunity" (
	id INTEGER NOT NULL,
	"Name" VARCHAR(255),
	"CloseDate" VARCHAR(255),
	"Amount" VARCHAR(255),
	"StageName" VARCHAR(255),
	"AccountId" VARCHAR(255),
	PRIMARY KEY (id)
);

INSERT INTO
	"Opportunity"
VALUES
	(
		1,
		'represent Opportunity',
		'2021-10-03',
		'136',
		'In Progress',
		'2'
	);

INSERT INTO
	"Opportunity"
VALUES
	(
		2,
		'yes Opportunity',
		'0000-01-01',
		'138',
		'New',
		'2'
	);

INSERT INTO
	"Opportunity"
VALUES
	(
		3,
		'another Opportunity',
		'2021-09-08',
		'192',
		'Closed Won',
		'2'
	);

INSERT INTO
	"Opportunity"
VALUES
	(
		4,
		'need Opportunity',
		'9999-01-23',
		'116',
		'New',
		'2'
	);

COMMIT;
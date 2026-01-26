BEGIN TRANSACTION;

CREATE TABLE "PricebookEntry" (
    id VARCHAR(255) NOT NULL,
    "Pricebook2Id" VARCHAR(255),
    "UnitPrice" VARCHAR(255),
    PRIMARY KEY (id)
);
INSERT INTO "PricebookEntry" VALUES('PricebookEntry-1', '01sSG00000Dsd89YAB', '100');
INSERT INTO "PricebookEntry" VALUES('PricebookEntry-2', 'Pricebook2-1', '200');
INSERT INTO "PricebookEntry" VALUES('PricebookEntry-3', '01sSG00000Dsd89', '300');
INSERT INTO "PricebookEntry" VALUES('PricebookEntry-4', NULL, '400');
INSERT INTO "PricebookEntry" VALUES('PricebookEntry-5', 'invalid-ref', '500');

CREATE TABLE "Pricebook2" (
    id VARCHAR(255) NOT NULL,
    "Name" VARCHAR(255),
    PRIMARY KEY (id)
);
INSERT INTO "Pricebook2" VALUES('Pricebook2-1', 'Standard Price Book');
INSERT INTO "Pricebook2" VALUES('Pricebook2-2', 'Partner Price Book');

CREATE TABLE "cumulusci_id_table" (
    id VARCHAR(255) NOT NULL,
    sf_id VARCHAR(18)
);
INSERT INTO "cumulusci_id_table" VALUES('Pricebook2-1', '01s000000000001AAA');
INSERT INTO "cumulusci_id_table" VALUES('Pricebook2-2', '01s000000000002AAA');

COMMIT;

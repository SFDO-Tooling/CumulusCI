BEGIN TRANSACTION;
CREATE TABLE "Account" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"AccountNumber" VARCHAR(255), 
	"Site" VARCHAR(255), 
	"Type" VARCHAR(255), 
	"Industry" VARCHAR(255), 
	"AnnualRevenue" VARCHAR(255), 
	"Rating" VARCHAR(255), 
	"Phone" VARCHAR(255), 
	"Fax" VARCHAR(255), 
	"Website" VARCHAR(255), 
	"Ownership" VARCHAR(255), 
	"Sic" VARCHAR(255), 
	"TickerSymbol" VARCHAR(255), 
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
	"Description" VARCHAR(255), 
	"Salutation" VARCHAR(255), 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"PersonTitle" VARCHAR(255), 
	"PersonEmail" VARCHAR(255), 
	"PersonDepartment" VARCHAR(255), 
	"PersonBirthdate" VARCHAR(255), 
	"PersonLeadSource" VARCHAR(255), 
	"PersonHomePhone" VARCHAR(255), 
	"PersonMobilePhone" VARCHAR(255), 
	"PersonOtherPhone" VARCHAR(255), 
	"PersonAssistantName" VARCHAR(255), 
	"PersonAssistantPhone" VARCHAR(255), 
	"PersonMailingStreet" VARCHAR(255), 
	"PersonMailingCity" VARCHAR(255), 
	"PersonMailingState" VARCHAR(255), 
	"PersonMailingPostalCode" VARCHAR(255), 
	"PersonMailingCountry" VARCHAR(255), 
	"PersonOtherStreet" VARCHAR(255), 
	"PersonOtherCity" VARCHAR(255), 
	"PersonOtherState" VARCHAR(255), 
	"PersonOtherPostalCode" VARCHAR(255), 
	"PersonOtherCountry" VARCHAR(255), 
	"IsPersonAccount" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Account" VALUES(1,'','','','Customer - Direct','Other','','','719-555-4157','','','','','','31 Greenrose Drive Unit 7','PuebloPueblo','Colorado','81006','United States','','','','','','','Ms.','Rylee','Hood','Student','rylee.hood@echigh.example.com','','','','','','','','','31 Greenrose Drive Unit 7','Pueblo','Colorado','81006','United States','','','','','','true',NULL);
INSERT INTO "Account" VALUES(2,'','','','Customer - Direct','Other','','','719-555-5117','','','','','','27 NW Overlook Road','Colorado Springs','Colorado','80907','United States','','','','','','','Ms.','Alanna','Preston','Student','alanna.preston@freenet.example.com','','','','','','','','','27 NW Overlook Road','Colorado Springs','Colorado','80907','United States','','','','','','true',NULL);
INSERT INTO "Account" VALUES(3,'','','','Customer - Direct','Other','','','719-555-8020','','','','','','8591 W Rockville Street','Salida','Colorado','81201','United States','','','','','','','Ms.','Mina','Charmchi','Student','mina.charmchi@pchs.example.com','','','','','','','','','8591 W Rockville Street','Salida','Colorado','81201','United States','','','','','','true',NULL);
INSERT INTO "Account" VALUES(4,'','','','Customer - Direct','Other','','','719-555-3725','','','','','','98 53rd Ave','Canon City','Colorado','81212','United States','','','','','','','Ms.','Ling','Xiang','Student','ling.xiang@freenet.example.com','','','','','','','','','98 53rd Ave','Canon City','Colorado','81212','United States','','','','','','true',NULL);
INSERT INTO "Account" VALUES(5,'','','','Customer - Direct','Other','','','303-555-3044','','','','','','519 West Cherry Street','Denver','Colorado','80227','United States','','','','','','','Mr.','Anson','Henderson','Student','anson.henderson@connect.example.com','','','','','','','','','519 West Cherry Street','Denver','Colorado','80227','United States','','','','','','true',NULL);
INSERT INTO "Account" VALUES(6,'','','','Customer - Direct','Other','','','303-555-5711','','','','','','261 North Arrowhead Ave','Denver','Colorado','80216','United States','','','','','','','Mr.','Corey','Valdez','Student','corey.valdez@connect.example.com','','','','','','','','','261 North Arrowhead Ave','Denver','Colorado','80216','United States','','','','','','true',NULL);
INSERT INTO "Account" VALUES(7,'','','','Customer - Direct','Other','','','720-555-4601','','','','','','701 Magnolia Street
Apt 402','Denver','Colorado','Colorado','United States','','','','','','','Mr.','Itoro','Idowu','Student','itoro.idowu@cstate.example.com','','','','','','','','','701 Magnolia Street
Apt 402','Denver','Colorado','Colorado','United States','','','','','','true',NULL);
INSERT INTO "Account" VALUES(8,'Grantwood City Council','','','Customer - Direct','Government','','','970-555-9633','','','','','','445 North Peak Road','Grantwood','Colorado','80522','United States','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','false',NULL);
INSERT INTO "Account" VALUES(9,'Takagawa Institute','','','Customer - Direct','Not For Profit','','','602-555-3542','','','','','','9833 Plateau Street','Phoenix','Arizona','85310','United States','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','false',NULL);
INSERT INTO "Account" VALUES(10,'Grantseeker Community: Self-Registered','','','','','','','','','','','','','','','','','','','','','','','Account initially assigned to self-registered users for the Grantseeker Community','','','','','','','','','','','','','','','','','','','','','','','','false',NULL);
INSERT INTO "Account" VALUES(11,'Hillside Elementary','','','Customer - Direct','Education','','','719-555-9914','','','','','','713 S. 8th Street','Englewood','Colorado','80110','United States','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','false',NULL);
INSERT INTO "Account" VALUES(12,'STEPS','','','Customer - Direct','Not For Profit','','','303-555-7541','','','','','','2920 Juniper Drive','Denver','Colorado','80230','United States','','','','','','','','','','','','','','','','','','','','','','','','','','','','','','false',NULL);
CREATE TABLE "Contact" (
	id INTEGER NOT NULL, 
	"Salutation" VARCHAR(255), 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Title" VARCHAR(255), 
	"Email" VARCHAR(255), 
	"Department" VARCHAR(255), 
	"Birthdate" VARCHAR(255), 
	"LeadSource" VARCHAR(255), 
	"Phone" VARCHAR(255), 
	"HomePhone" VARCHAR(255), 
	"OtherPhone" VARCHAR(255), 
	"Fax" VARCHAR(255), 
	"AssistantName" VARCHAR(255), 
	"AssistantPhone" VARCHAR(255), 
	"MailingStreet" VARCHAR(255), 
	"MailingCity" VARCHAR(255), 
	"MailingState" VARCHAR(255), 
	"MailingPostalCode" VARCHAR(255), 
	"MailingCountry" VARCHAR(255), 
	"OtherStreet" VARCHAR(255), 
	"OtherCity" VARCHAR(255), 
	"OtherState" VARCHAR(255), 
	"OtherPostalCode" VARCHAR(255), 
	"OtherCountry" VARCHAR(255), 
	"Description" VARCHAR(255), 
	"IsPersonAccount" VARCHAR(255), 
	"AccountId" VARCHAR(255), 
	"ReportsToId" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Contact" VALUES(1,'Ms.','Rylee','Hood','Student','rylee.hood@echigh.example.com','','','','719-555-4157','','','','','','31 Greenrose Drive Unit 7','Pueblo','Colorado','81006','United States','','','','','','','true','1','',NULL);
INSERT INTO "Contact" VALUES(2,'Ms.','Alanna','Preston','Student','alanna.preston@freenet.example.com','','','','719-555-5117','','','','','','27 NW Overlook Road','Colorado Springs','Colorado','80907','United States','','','','','','','true','2','',NULL);
INSERT INTO "Contact" VALUES(3,'Ms.','Mina','Charmchi','Student','mina.charmchi@pchs.example.com','','','','719-555-8020','','','','','','8591 W Rockville Street','Salida','Colorado','81201','United States','','','','','','','true','3','',NULL);
INSERT INTO "Contact" VALUES(4,'Ms.','Ling','Xiang','Student','ling.xiang@freenet.example.com','','','','719-555-3725','','','','','','98 53rd Ave','Canon City','Colorado','81212','United States','','','','','','','true','4','',NULL);
INSERT INTO "Contact" VALUES(5,'Mr.','Anson','Henderson','Student','anson.henderson@connect.example.com','','','','303-555-3044','','','','','','519 West Cherry Street','Denver','Colorado','80227','United States','','','','','','','true','5','',NULL);
INSERT INTO "Contact" VALUES(6,'Mr.','Corey','Valdez','Student','corey.valdez@connect.example.com','','','','303-555-5711','','','','','','261 North Arrowhead Ave','Denver','Colorado','80216','United States','','','','','','','true','6','',NULL);
INSERT INTO "Contact" VALUES(7,'Mr.','Itoro','Idowu','Student','itoro.idowu@cstate.example.com','','','','720-555-4601','','','','','','701 Magnolia Street
Apt 402','Denver','Colorado','Colorado','United States','','','','','','','true','7','',NULL);
INSERT INTO "Contact" VALUES(8,'Mr.','Devon','Berger','Literacy Coach','devon.berger@hillside-elementary.example.com','','','','719-555-9914','','','','','','713 S. 8th Street','Englewood','Colorado','80110','United States','','','','','','','false','11','',NULL);
INSERT INTO "Contact" VALUES(9,'Ms.','Ellen','Perez','Program Coordinator','ellen.perez@steps.example.com','','','','303-555-7541','','','','','','2920 Juniper Drive','Denver','Colorado','80230','United States','','','','','','','false','12','10',NULL);
INSERT INTO "Contact" VALUES(10,'Ms.','Grace','Walker','Development Director','grace.walker@steps.example.com','','','','303-555-7540','','','','','','2920 Juniper Drive','Denver','Colorado','80230','United States','','','','','','','false','12','',NULL);
INSERT INTO "Contact" VALUES(11,'Mr.','Jermaine','Harmon','Intern','jermaine.harmon@steps.example.com','','','','303-555-7540','','','','','','2920 Juniper Drive','Denver','Colorado','80230','United States','','','','','','','false','12','',NULL);
INSERT INTO "Contact" VALUES(12,'Mr.','Dillon','Whitaker','Assistant City Manager','dillon.whitaker@gwcity.example.com','','','','719-555-2417','','','','','','445 North Peak Road','Grantwood','Colorado','80522','United States','','','','','','','false','8','',NULL);
INSERT INTO "Contact" VALUES(13,'Ms.','Adriana','Atterberry','Grants Manager','adriana.atterberry@takagawa-institute.example.com','','','','602-555-3543','','','','','','9834 Plateau Street','Phoenix','Arizona','85310','United States','','','','','','','false','9','14',NULL);
INSERT INTO "Contact" VALUES(14,'Dr.','Meiko','Takagawa','Executive Director','meiko.takagawa@takagawa-institute.example.com','','','','602-555-3542','','','','','','9833 Plateau Street','Phoenix','Arizona','85310','United States','','','','','','','false','9','',NULL);
CREATE TABLE "Group" (
	id INTEGER NOT NULL, 
	"DeveloperName" VARCHAR(255), 
	"Type" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Group" VALUES(1,'GrantMaker','Role',NULL);
INSERT INTO "Group" VALUES(2,'UUserCustomerPersonAccount','Role',NULL);
INSERT INTO "Group" VALUES(3,'HillsideElementaryCustomerUser','Role',NULL);
INSERT INTO "Group" VALUES(4,'GrantMaker','RoleAndSubordinates',NULL);
INSERT INTO "Group" VALUES(5,'UUserCustomerPersonAccount','RoleAndSubordinates',NULL);
INSERT INTO "Group" VALUES(6,'HillsideElementaryCustomerUser','RoleAndSubordinates',NULL);
INSERT INTO "Group" VALUES(7,'CEO','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(8,'CFO','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(9,'ChannelSalesTeam','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(10,'COO','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(11,'CustomerSupportInternational','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(12,'CustomerSupportNorthAmerica','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(13,'DirectorChannelSales','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(14,'DirectorDirectSales','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(15,'EasternSalesTeam','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(16,'InstallationRepairServices','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(17,'MarketingTeam','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(18,'SVPCustomerServiceSupport','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(19,'SVPHumanResources','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(20,'SVPSalesMarketing','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(21,'VPInternationalSales','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(22,'VPMarketing','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(23,'VPNorthAmericanSales','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(24,'WesternSalesTeam','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(25,'GrantMaker','RoleAndSubordinatesInternal',NULL);
INSERT INTO "Group" VALUES(26,'AllPartnerUsers','PRMOrganization',NULL);
INSERT INTO "Group" VALUES(27,'AllInternalUsers','Organization',NULL);
INSERT INTO "Group" VALUES(28,'AllCustomerPortalUsers','AllCustomerPortal',NULL);
INSERT INTO "Group" VALUES(29,'Funding_Program_Portal','GuestUserGroup',NULL);
CREATE TABLE "Profile" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"UserType" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "Profile" VALUES(2,'Grantseeker Plus Login','PowerCustomerSuccess',NULL);
INSERT INTO "Profile" VALUES(3,'Standard Guest','Guest',NULL);
INSERT INTO "Profile" VALUES(4,'Funding Program Portal Profile','Guest',NULL);
INSERT INTO "Profile" VALUES(5,'Grantseeker','CspLitePortal',NULL);
INSERT INTO "Profile" VALUES(6,'Grantseeker Login','CspLitePortal',NULL);
INSERT INTO "Profile" VALUES(7,'Grantseeker Plus','PowerCustomerSuccess',NULL);
INSERT INTO "Profile" VALUES(8,'System Administrator','Standard',NULL);
INSERT INTO "Profile" VALUES(9,'Analytics Cloud Integration User','Standard',NULL);
INSERT INTO "Profile" VALUES(10,'Analytics Cloud Security User','Standard',NULL);
INSERT INTO "Profile" VALUES(11,'Chatter Free User','CsnOnly',NULL);
INSERT INTO "Profile" VALUES(13,'Company Communities User','Standard',NULL);
INSERT INTO "Profile" VALUES(14,'Standard Platform User','Standard',NULL);
INSERT INTO "Profile" VALUES(15,'Customer Community Login User','CspLitePortal',NULL);
INSERT INTO "Profile" VALUES(16,'Cross Org Data Proxy User','Standard',NULL);
INSERT INTO "Profile" VALUES(18,'Work.com Only User','Standard',NULL);
INSERT INTO "Profile" VALUES(19,'Customer Portal Manager Custom','PowerCustomerSuccess',NULL);
INSERT INTO "Profile" VALUES(20,'Identity User','Standard',NULL);
INSERT INTO "Profile" VALUES(21,'Customer Community Plus User','PowerCustomerSuccess',NULL);
INSERT INTO "Profile" VALUES(22,'Silver Partner User','PowerPartner',NULL);
INSERT INTO "Profile" VALUES(23,'High Volume Customer Portal','CspLitePortal',NULL);
INSERT INTO "Profile" VALUES(24,'Gold Partner User','PowerPartner',NULL);
INSERT INTO "Profile" VALUES(25,'Customer Portal Manager Standard','PowerCustomerSuccess',NULL);
INSERT INTO "Profile" VALUES(26,'Force.com - App Subscription User','Standard',NULL);
INSERT INTO "Profile" VALUES(27,'Customer Community Plus Login User','PowerCustomerSuccess',NULL);
INSERT INTO "Profile" VALUES(28,'Partner App Subscription User','Standard',NULL);
INSERT INTO "Profile" VALUES(29,'External Identity User','CspLitePortal',NULL);
INSERT INTO "Profile" VALUES(30,'Partner Community User','PowerPartner',NULL);
INSERT INTO "Profile" VALUES(31,'Partner Community Login User','PowerPartner',NULL);
INSERT INTO "Profile" VALUES(32,'Customer Community User','CspLitePortal',NULL);
INSERT INTO "Profile" VALUES(33,'Force.com - Free User','Standard',NULL);
INSERT INTO "Profile" VALUES(34,'Chatter Moderator User','CsnOnly',NULL);
INSERT INTO "Profile" VALUES(35,'Chatter External User','CsnOnly',NULL);
INSERT INTO "Profile" VALUES(36,'High Volume Customer Portal User','CspLitePortal',NULL);
INSERT INTO "Profile" VALUES(37,'Solution Manager','Standard',NULL);
INSERT INTO "Profile" VALUES(38,'Read Only','Standard',NULL);
INSERT INTO "Profile" VALUES(39,'Custom: Sales Profile','Standard',NULL);
INSERT INTO "Profile" VALUES(40,'Custom: Marketing Profile','Standard',NULL);
INSERT INTO "Profile" VALUES(41,'Custom: Support Profile','Standard',NULL);
INSERT INTO "Profile" VALUES(42,'Marketing User','Standard',NULL);
INSERT INTO "Profile" VALUES(43,'Contract Manager','Standard',NULL);
INSERT INTO "Profile" VALUES(44,'Standard User','Standard',NULL);
INSERT INTO "Profile" VALUES(45,'CPQ Integration User','Standard',NULL);
CREATE TABLE "User" (
	id INTEGER NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Username" VARCHAR(255), 
	"Email" VARCHAR(255), 
	"Alias" VARCHAR(255), 
	"CommunityNickname" VARCHAR(255), 
	"CompanyName" VARCHAR(255), 
	"IsActive" VARCHAR(255),
	"ProfileId" VARCHAR(255), 
	"ContactId" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "User" VALUES(1,'Automated','Process','autoproc@00d3b0000005rg1uaa','autoproc@00d3b0000005rg1uaa','autoproc','automatedprocess','New Org Name','true','00e3B000000SL1TQAW','',NULL);
INSERT INTO "User" VALUES(2,'','Data.com Clean','automatedclean@00d3b0000005rg1uaa','automatedclean@00d3b0000005rg1uaa','autocln','automatedclean1.48731721896167E12','New Org Name','true','00e3B000000SL1TQAW','',NULL);
INSERT INTO "User" VALUES(3,'','-736615976','_ky66tqieyd@sqpiklbgvy.com','-736615976@-736615976.com','-7366159','User15980217959849202689','','false','7','',NULL);
INSERT INTO "User" VALUES(4,'','-736615939','_jjjcaertrl@ubyct826bz.com','-736615939@-736615939.com','-7366159','User15980217897281874037','','false','2','',NULL);
INSERT INTO "User" VALUES(5,'','-736615938','_nuwb2blpms@vt5ckwzdc0.com','-736615938@-736615938.com','-7366159','User15980217913323701524','','false','2','',NULL);
INSERT INTO "User" VALUES(6,'','-736615937','_4m3dsxrloo@nf9fn9ehwa.com','-736615937@-736615937.com','-7366159','User15980217921416973397','','false','2','',NULL);
INSERT INTO "User" VALUES(7,'','-736615980','_sqtub7grtk@gofbgyvhby.com','-736615980@-736615980.com','-7366159','User15980217929182512362','','false','7','',NULL);
INSERT INTO "User" VALUES(8,'','-736615979','_z1dejz3kcn@jxgx0i45xp.com','-736615979@-736615979.com','-7366159','User1598021793759401124','','false','7','',NULL);
INSERT INTO "User" VALUES(9,'','-736615978','_zhvgjdaxvg@euwhemyg0m.com','-736615978@-736615978.com','-7366159','User15980217945117545709','','false','7','',NULL);
INSERT INTO "User" VALUES(10,'','-736615977','_tskpgfqafv@fgiyffpjl0.com','-736615977@-736615977.com','-7366159','User15980217952795519070','','false','7','',NULL);
INSERT INTO "User" VALUES(11,'Rylee','Hood','rylee.hood@echigh.example.com','rylee.hood@echigh.example.com','rylee','Rylee','','true','2','1',NULL);
INSERT INTO "User" VALUES(12,'Alanna','Preston','alanna.preston@freenet.example.com','alanna.preston@freenet.example.com','alanna','Alanna','','true','2','2',NULL);
INSERT INTO "User" VALUES(13,'Mina','Charmchi','mina.charmchi@pchs.example.com','mina.charmchi@pchs.example.com','mina','Mina','','true','2','3',NULL);
INSERT INTO "User" VALUES(14,'Ling','Xiang','ling.xiang@freenet.example.com','ling.xiang@freenet.example.com','ling','Ling','','true','7','4',NULL);
INSERT INTO "User" VALUES(15,'Anson','Henderson','anson.henderson@connect.example.com','anson.henderson@connect.example.com','anson','Anson','','true','7','5',NULL);
INSERT INTO "User" VALUES(16,'Corey','Valdez','corey.valdez@connect.example.com','corey.valdez@connect.example.com','corey','Corey','','true','7','6',NULL);
INSERT INTO "User" VALUES(17,'Itoro','Idowu','itoro.idowu@cstate.example.com','itoro.idowu@cstate.example.com','itoro','Itoro','','true','7','7',NULL);
INSERT INTO "User" VALUES(18,'Devon','Berger','devon.berger@hillside-elementary.example.com','devon.berger@hillside-elementary.example.com','devon','Devon','','true','7','8',NULL);
INSERT INTO "User" VALUES(19,'Funding Program Portal','Site Guest User','funding_program_portal@sandbox-force-app-5557-dev-ed-174114bc3e1.cs50.force.com','spelak@salesforce.com','guest','Funding_Program_Portal','','true','4','',NULL);
INSERT INTO "User" VALUES(20,'Integration','User','integration@00d3b0000005rg1uaa.com','integration@example.com','integ','integration1.4407085834085586E12','New Org Name','true','9','',NULL);
INSERT INTO "User" VALUES(21,'Security','User','insightssecurity@00d3b0000005rg1uaa.com','insightssecurity@example.com','sec','insightssecurity1.4407085845464958E12','New Org Name','true','10','',NULL);
INSERT INTO "User" VALUES(22,'User','User','test-ghyxmoew8dy0@example.com','spelak@salesforce.com','UUser','test-ghyxmoew8dy0','SFDO-Grants - Dev Org','true','8','',NULL);
INSERT INTO "User" VALUES(23,'','-736615975','_s9d3end6hb@rlwgy0di4k.com','-736615975@-736615975.com','-7366159','User15980217970329790977','','false','6','',NULL);
INSERT INTO "User" VALUES(24,'','-736615974','_u3bmkvnpx9@pdxhytdjwn.com','-736615974@-736615974.com','-7366159','User15980217978053929346','','false','6','',NULL);
INSERT INTO "User" VALUES(25,'','-736615973','_pid0jans5e@zyu4y11ojm.com','-736615973@-736615973.com','-7366159','User15980217985321552399','','false','6','',NULL);
INSERT INTO "User" VALUES(26,'Ellen','Perez','ellen.perez@steps.example.com','ellen.perez@steps.example.com','ellen','Ellen','','true','6','9',NULL);
INSERT INTO "User" VALUES(27,'Grace','Walker','grace.walker@steps.example.com','grace.walker@steps.example.com','grace','Grace','','true','6','10',NULL);
INSERT INTO "User" VALUES(28,'Meiko','Takagawa','meiko.takagawa@takagawa-institute.example.com','meiko.takagawa@takagawa-institute.example.com','meiko','Meiko','','true','6','14',NULL);
INSERT INTO "User" VALUES(29,'','Chatter Expert','chatty.00d3b0000005rg1uaa.hotvchkrmafg@chatter.salesforce.com','noreply@chatter.salesforce.com','Chatter','Chatter Expert','New Org Name','true','11','',NULL);
CREATE TABLE community_users (
	id INTEGER NOT NULL, 
	"FirstName" VARCHAR(255), 
	"LastName" VARCHAR(255), 
	"Email" VARCHAR(255), 
	"Username" VARCHAR(255), 
	"Alias" VARCHAR(255), 
	"LocaleSidKey" VARCHAR(255), 
	"TimeZoneSidKey" VARCHAR(255), 
	"LanguageLocaleKey" VARCHAR(255), 
	"EmailEncodingKey" VARCHAR(255), 
	"Phone" VARCHAR(255), 
	"Fax" VARCHAR(255), 
	"Street" VARCHAR(255), 
	"City" VARCHAR(255), 
	"State" VARCHAR(255), 
	"PostalCode" VARCHAR(255), 
	"Country" VARCHAR(255), 
	"CommunityNickname" VARCHAR(255), 
	"CompanyName" VARCHAR(255), 
	"IsActive" VARCHAR(255),
	"ProfileId" VARCHAR(255), 
	"ContactId" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "community_users" VALUES(1,'Automated','Process','autoproc@00d3b0000005rg1uaa','autoproc@00d3b0000005rg1uaa','autoproc','en_US','America/Los_Angeles','en_US','ISO-8859-1','','','1 Market','San Francisco','CA','94015','US','automatedprocess','New Org Name','true','00e3B000000SL1TQAW','',NULL);
INSERT INTO "community_users" VALUES(2,'','Data.com Clean','automatedclean@00d3b0000005rg1uaa','automatedclean@00d3b0000005rg1uaa','autocln','en_US','America/Los_Angeles','en_US','ISO-8859-1','','','1 Market','San Francisco','CA','94015','US','automatedclean1.48731721896167E12','New Org Name','true','00e3B000000SL1TQAW','',NULL);
INSERT INTO "community_users" VALUES(3,'','-736615976','-736615976@-736615976.com','_ky66tqieyd@sqpiklbgvy.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217959849202689','','false','7','',NULL);
INSERT INTO "community_users" VALUES(4,'','-736615939','-736615939@-736615939.com','_jjjcaertrl@ubyct826bz.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217897281874037','','false','2','',NULL);
INSERT INTO "community_users" VALUES(5,'','-736615938','-736615938@-736615938.com','_nuwb2blpms@vt5ckwzdc0.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217913323701524','','false','2','',NULL);
INSERT INTO "community_users" VALUES(6,'','-736615937','-736615937@-736615937.com','_4m3dsxrloo@nf9fn9ehwa.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217921416973397','','false','2','',NULL);
INSERT INTO "community_users" VALUES(7,'','-736615980','-736615980@-736615980.com','_sqtub7grtk@gofbgyvhby.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217929182512362','','false','7','',NULL);
INSERT INTO "community_users" VALUES(8,'','-736615979','-736615979@-736615979.com','_z1dejz3kcn@jxgx0i45xp.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User1598021793759401124','','false','7','',NULL);
INSERT INTO "community_users" VALUES(9,'','-736615978','-736615978@-736615978.com','_zhvgjdaxvg@euwhemyg0m.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217945117545709','','false','7','',NULL);
INSERT INTO "community_users" VALUES(10,'','-736615977','-736615977@-736615977.com','_tskpgfqafv@fgiyffpjl0.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217952795519070','','false','7','',NULL);
INSERT INTO "community_users" VALUES(11,'Rylee','Hood','rylee.hood@echigh.example.com','rylee.hood@echigh.example.com','rylee','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Rylee','','true','2','1',NULL);
INSERT INTO "community_users" VALUES(12,'Alanna','Preston','alanna.preston@freenet.example.com','alanna.preston@freenet.example.com','alanna','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Alanna','','true','2','2',NULL);
INSERT INTO "community_users" VALUES(13,'Mina','Charmchi','mina.charmchi@pchs.example.com','mina.charmchi@pchs.example.com','mina','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Mina','','true','2','3',NULL);
INSERT INTO "community_users" VALUES(14,'Ling','Xiang','ling.xiang@freenet.example.com','ling.xiang@freenet.example.com','ling','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Ling','','true','7','4',NULL);
INSERT INTO "community_users" VALUES(15,'Anson','Henderson','anson.henderson@connect.example.com','anson.henderson@connect.example.com','anson','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Anson','','true','7','5',NULL);
INSERT INTO "community_users" VALUES(16,'Corey','Valdez','corey.valdez@connect.example.com','corey.valdez@connect.example.com','corey','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Corey','','true','7','6',NULL);
INSERT INTO "community_users" VALUES(17,'Itoro','Idowu','itoro.idowu@cstate.example.com','itoro.idowu@cstate.example.com','itoro','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Itoro','','true','7','7',NULL);
INSERT INTO "community_users" VALUES(18,'Devon','Berger','devon.berger@hillside-elementary.example.com','devon.berger@hillside-elementary.example.com','devon','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Devon','','true','7','8',NULL);
INSERT INTO "community_users" VALUES(19,'Funding Program Portal','Site Guest User','spelak@salesforce.com','funding_program_portal@sandbox-force-app-5557-dev-ed-174114bc3e1.cs50.force.com','guest','en_US','GMT','en_US','ISO-8859-1','','','','','','','','Funding_Program_Portal','','true','4','',NULL);
INSERT INTO "community_users" VALUES(20,'Integration','User','integration@example.com','integration@00d3b0000005rg1uaa.com','integ','en_US','America/Los_Angeles','en_US','ISO-8859-1','','','1 Market','San Francisco','CA','94015','US','integration1.4407085834085586E12','New Org Name','true','9','',NULL);
INSERT INTO "community_users" VALUES(21,'Security','User','insightssecurity@example.com','insightssecurity@00d3b0000005rg1uaa.com','sec','en_US','America/Los_Angeles','en_US','ISO-8859-1','','','1 Market','San Francisco','CA','94015','US','insightssecurity1.4407085845464958E12','New Org Name','true','10','',NULL);
INSERT INTO "community_users" VALUES(22,'User','User','spelak@salesforce.com','test-ghyxmoew8dy0@example.com','UUser','en_US','America/Los_Angeles','en_US','ISO-8859-1','','','','','','','US','test-ghyxmoew8dy0','SFDO-Grants - Dev Org','true','8','',NULL);
INSERT INTO "community_users" VALUES(23,'','-736615975','-736615975@-736615975.com','_s9d3end6hb@rlwgy0di4k.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217970329790977','','false','6','',NULL);
INSERT INTO "community_users" VALUES(24,'','-736615974','-736615974@-736615974.com','_u3bmkvnpx9@pdxhytdjwn.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217978053929346','','false','6','',NULL);
INSERT INTO "community_users" VALUES(25,'','-736615973','-736615973@-736615973.com','_pid0jans5e@zyu4y11ojm.com','-7366159','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','User15980217985321552399','','false','6','',NULL);
INSERT INTO "community_users" VALUES(26,'Ellen','Perez','ellen.perez@steps.example.com','ellen.perez@steps.example.com','ellen','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Ellen','','true','6','9',NULL);
INSERT INTO "community_users" VALUES(27,'Grace','Walker','grace.walker@steps.example.com','grace.walker@steps.example.com','grace','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Grace','','true','6','10',NULL);
INSERT INTO "community_users" VALUES(28,'Meiko','Takagawa','meiko.takagawa@takagawa-institute.example.com','meiko.takagawa@takagawa-institute.example.com','meiko','en_US','America/Los_Angeles','en_US','UTF-8','','','','','','','','Meiko','','true','6','14',NULL);
INSERT INTO "community_users" VALUES(29,'','Chatter Expert','noreply@chatter.salesforce.com','chatty.00d3b0000005rg1uaa.hotvchkrmafg@chatter.salesforce.com','Chatter','en_US','America/Los_Angeles','en_US','ISO-8859-1','','','1 Market','San Francisco','CA','94015','US','Chatter Expert','New Org Name','true','11','',NULL);
CREATE TABLE "outfunds__Funding_Program__c" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"outfunds__Description__c" VARCHAR(255), 
	"outfunds__End_Date__c" VARCHAR(255), 
	"outfunds__Start_Date__c" VARCHAR(255), 
	"outfunds__Status__c" VARCHAR(255), 
	"outfunds__Top_Level__c" VARCHAR(255), 
	"outfunds__Total_Program_Amount__c" VARCHAR(255), 
	"outfunds__Parent_Funding_Program__c" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "outfunds__Funding_Program__c" VALUES(1,'Kumar Endowment Scholarship','The Kumar family graciously sponsors the Kumar Endowment Scholarship Fund for high school students who have made a positive impact in their local community. This fund awards $2,000 scholarships every 4 years to ten students seeking higher education. Eligible expenses include tuition, room and board, fees, and books during the academic year.','2020-07-31','2020-01-15','In progress','false','200000.0','3',NULL);
INSERT INTO "outfunds__Funding_Program__c" VALUES(2,'Successful Scholars Grant','The Successful Scholars Grant provides funding to select non-profits and education institutes to enable students to excel in their academics. Past initiatives created by previous grantees include after-school tutoring, early literacy programs, and college preparation courses.','2020-08-14','2019-08-15','In progress','false','250000.0','3',NULL);
INSERT INTO "outfunds__Funding_Program__c" VALUES(3,'Education','','','','In progress','true','','',NULL);
INSERT INTO "outfunds__Funding_Program__c" VALUES(4,'Community Impact','','','','In progress','true','','',NULL);
INSERT INTO "outfunds__Funding_Program__c" VALUES(5,'Relief and Reinvestment Grant','The Relief and Reinvestment Grant provides financial assistance in the form of grants to small businesses experiencing temporary revenue loss due to unforeseen circumstances, such as a natural disaster or economic crisis. Grants of up to $10,000 are awarded to select small businesses to help offset lost revenue. This fund can be used for:
        * Rent and utilities
        * Payroll
        * Outstanding debt
        * Technology upgrades
        * Immediate operation costs','2021-01-31','2020-02-01','In progress','false','300000.0','4',NULL);
INSERT INTO "outfunds__Funding_Program__c" VALUES(6,'Strategic Nonprofit Development','','','','Planned','true','','',NULL);
CREATE TABLE "outfunds__Funding_Program__share" (
	id INTEGER NOT NULL, 
	"AccessLevel" VARCHAR(255), 
	"RowCause" VARCHAR(255), 
	"ParentID" VARCHAR(255), 
	"UserOrGroupId" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "outfunds__Funding_Program__share" VALUES(1,'All','Owner','1','0053B000003f589QAA',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(2,'All','Owner','2','0053B000003f589QAA',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(3,'All','Owner','3','0053B000003f589QAA',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(4,'All','Owner','4','0053B000003f589QAA',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(5,'All','Owner','5','0053B000003f589QAA',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(6,'All','Owner','6','0053B000003f589QAA',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(7,'Read','Manual','1','28',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(8,'Read','Manual','2','28',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(9,'Read','Manual','4','28',NULL);
INSERT INTO "outfunds__Funding_Program__share" VALUES(10,'Read','Manual','5','28',NULL);
CREATE TABLE "outfunds__Funding_Request__c" (
	id INTEGER NOT NULL, 
	"Name" VARCHAR(255), 
	"outfunds__Application_Date__c" VARCHAR(255), 
	"outfunds__Awarded_Amount__c" VARCHAR(255), 
	"outfunds__Awarded_Date__c" VARCHAR(255), 
	"outfunds__Close_Date__c" VARCHAR(255), 
	"outfunds__Closed_reason__c" VARCHAR(255), 
	"outfunds__Geographical_Area_Served__c" VARCHAR(255), 
	"outfunds__Population_Served__c" VARCHAR(255), 
	"outfunds__Recommended_Amount__c" VARCHAR(255), 
	"outfunds__Requested_Amount__c" VARCHAR(255), 
	"outfunds__Requested_For__c" VARCHAR(255), 
	"outfunds__Status__c" VARCHAR(255), 
	"outfunds__Term_End_Date__c" VARCHAR(255), 
	"outfunds__Term_Start_Date__c" VARCHAR(255), 
	"outfunds__Terms__c" VARCHAR(255), 
	"outfunds__Applying_Contact__c" VARCHAR(255), 
	"outfunds__Applying_Organization__c" VARCHAR(255), 
	"outfunds__FundingProgram__c" VARCHAR(255), 
	"OwnerId" VARCHAR(255), 
	record_type VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "outfunds__Funding_Request__c" VALUES(1,'Kumar Endowment Scholarship: Itoro Idowu','2016-04-15','8000.0','2016-07-21','2020-05-01','Graduated','','Children and Youth','8000.0','8000.0','','Fully Disbursed','2020-05-01','2016-08-15','4 years','7','7','1','17',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(2,'Kumar Endowment Scholarship: Ling Xiang','2020-05-04','','','','','','Children and Youth','','8000.0','','Submitted','','','','4','4','1','14',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(3,'Kumar Endowment Scholarship: Anson Henderson','2019-04-26','','','2019-05-01','Does not meet requirements','','Children and Youth','','8000.0','','Rejected','','','','5','5','1','15',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(4,'Kumar Endowment Scholarship: Corey Valdez','2020-05-21','','','','','','Children and Youth','','8000.0','','Submitted','','','','6','6','1','16',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(5,'Takagawa Institute: Relief and Reinvestment Grant','2020-03-12','10000.0','2020-03-29','2020-03-29','Fully awarded.','Country','Immigrants and Refugees','10000.0','10000.0','','Fully Disbursed','2021-03-28','2020-03-29','One time payment with one year follow up','14','9','5','28',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(6,'Skills for Success','2019-03-22','40000.0','2019-05-15','','','Region','Adults;Women','40000.0','40000.0','Skills for Success addresses an existing gap for at-risk women seeking to learn technical and soft skills to help them find gainful employment in the community. Participants of the program receive:

* Vouchers for free community college courses on select topics, such as bookkeeping, computer literacy, and communication skills.
* Help developing a resume and interview preparation. 
* One-on-one mentoring with a female business owner in the community.
* Ongoing support from the STEPS staff.','Awarded','2020-05-31','2019-06-01','1 year','10','12','4','27',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(7,'Skills for Success','2020-06-01','','','','','Region','Adults;Women','','46000.0','Skills for Success addresses an existing gap for at-risk women seeking to learn technical and soft skills to help them find gainful employment in the community. Participants of the program receive:

* Vouchers for free community college courses on select topics, such as bookkeeping, computer literacy, and communication skills.
* Help developing a resume and interview preparation. 
* One-on-one mentoring with a female business owner in the community.
* Ongoing support from the STEPS staff.','In progress','','','1 year','10','12','4','27',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(8,'Eager Beavers Read!','2019-04-26','15000.0','2019-07-10','','','City','Children and Youth','15000.0','15000.0','Eager Beavers Read! is an after school program that helps foster a love of reading in our 1st - 5th grade classes and also provides a safe place for students to go between 3:00 pm and 4:30 pm. Younger children will be paired up with an older student to help expand their early literacy skills, while older students work to develop mentoring skills and confidence.','Awarded','2022-08-14','2019-08-15','3 years','8','11','2','18',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(9,'Kumar Endowment Scholarship: Alanna Preston','2018-05-12','8000.0','2018-08-01','','','','Children and Youth','8000.0','8000.0','','Awarded','2022-05-01','2018-08-15','4 years','2','2','1','12',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(10,'Kumar Endowment Scholarship: Mina Charmchi','2020-05-02','','','','','','Children and Youth','','8000.0','','In Review','','','','3','3','1','13',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(11,'Grantwood City Food Bank','','','','','','City','Below Poverty level;Economically Disadvantaged People;Homeless','','','Grantwood City Food Bank','In progress','','','','','','4','22',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(12,'Grantwood City Food Bank','','','','','','City','Below Poverty level;Economically Disadvantaged People;Homeless','','100000.0','Grantwood City Food Bank','In progress','','','','','8','4','22',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(13,'Kumar Scholarship Fund Application: Rylee Hood','2020-06-12','','','','','','Children and Youth','','8000.0','','In progress','','','','1','1','1','11',NULL);
INSERT INTO "outfunds__Funding_Request__c" VALUES(14,'STEPS to Leadership','2020-02-17','28000.0','','','','Region','Adults;Women','28000.0','28000.0','STEPS to Leadership is a proposed program that came from requests for additional leadership training for our graduates from Skills for Success, a successful program we currently offer to at-risk women in the community. After completing Skills for Success, graduates can learn leadership skills through various trainings, seminars, and one-on-one mentoring that will help prepare these future female leaders.','Submitted','','','','9','12','4','26',NULL);
COMMIT;

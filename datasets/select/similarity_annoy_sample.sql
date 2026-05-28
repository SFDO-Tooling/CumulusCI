
BEGIN TRANSACTION;

CREATE TABLE "Account" (
    id VARCHAR(255) NOT NULL,
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
    "ParentId" VARCHAR(255),
    PRIMARY KEY (id)
);

CREATE TABLE "Contact" (
    id VARCHAR(255) NOT NULL,
    "FirstName" VARCHAR(255),
    "LastName" VARCHAR(255),
    "Salutation" VARCHAR(255),
    "Email" VARCHAR(255),
    "Phone" VARCHAR(255),
    "MobilePhone" VARCHAR(255),
    "Title" VARCHAR(255),
    "Birthdate" VARCHAR(255),
    "AccountId" VARCHAR(255),
    PRIMARY KEY (id)
);

-- Insert Account records
INSERT INTO "Account" VALUES('Account-6','Tucker, Roberts and Young','Future-proofed bi-directional encryption','','','','','','','','','','','','715.903.8280x689','','','69532987','');
INSERT INTO "Account" VALUES('Account-7','Richardson, Jones and Chen','Up-sized radical function','','','','','','','','','','','','368-764-8992','','','60964432','');
INSERT INTO "Account" VALUES('Account-8','Perkins, Johnson and Schroeder','Ameliorated 24/7 analyzer','','','','','','','','','','','','(678)277-9800x041','','','92641585','');
INSERT INTO "Account" VALUES('Account-9','Davis-Hernandez','Horizontal well-modulated secured line','','','','','','','','','','','','399-965-8911x480','','','41592661','');
INSERT INTO "Account" VALUES('Account-10','Acevedo-Lawson','Reverse-engineered 3rdgeneration approach','','','','','','','','','','','','3065087056','','','65959628','');
INSERT INTO "Account" VALUES('Account-11','Harris-Schroeder','Digitized tangible forecast','','','','','','','','','','','','5643586493','','','36154428','');
INSERT INTO "Account" VALUES('Account-12','Anderson LLC','Total multi-state throughput','','','','','','','','','','','','122.508.0623x6277','','','58454581','');
INSERT INTO "Account" VALUES('Account-13','Padilla-Sullivan','Universal disintermediate concept','','','','','','','','','','','','001-882-804-5645','','','47157364','');
INSERT INTO "Account" VALUES('Account-14','Owens Group','Configurable high-level portal','','','','','','','','','','','','(053)422-8886x706','','','52014732','');
INSERT INTO "Account" VALUES('Account-15','Ferguson-Ford','Robust upward-trending moratorium','','','','','','','','','','','','001-873-516-2659x5043','','','89903758','');
INSERT INTO "Account" VALUES('Account-16','Chambers-Nelson','Operative multimedia Graphic Interface','','','','','','','','','','','','106.252.9110','','','6017392','Account-2');
INSERT INTO "Account" VALUES('Account-17','Davidson, Johnson and Wilson','Persistent 4thgeneration archive','','','','','','','','','','','','(148)041-7089x1879','','','7645239','Account-3');
INSERT INTO "Account" VALUES('Account-18','Smith-Lee','Diverse disintermediate benchmark','','','','','','','','','','','','+1-860-127-9836x780','','','39175426','Account-5');
INSERT INTO "Account" VALUES('Account-19','Silva, Avila and Adkins','Future-proofed background policy','','','','','','','','','','','','001-713-221-4818x3867','','','3357478','');
INSERT INTO "Account" VALUES('Account-20','Anderson, Harrington and Norton','User-friendly systematic functionalities','','','','','','','','','','','','466.416.8129','','','50482193','');
INSERT INTO "Account" VALUES('Account-21','Bell-Armstrong','Operative human-resource info-mediaries','','','','','','','','','','','','572-522-6700x04982','','','59786157','');
INSERT INTO "Account" VALUES('Account-22','Camacho, Rose and Dixon','Persevering optimizing paradigm','','','','','','','','','','','','211.758.9395x3663','','','46438696','');
INSERT INTO "Account" VALUES('Account-23','Jackson PLC','Optional system-worthy array','','','','','','','','','','','','374.939.1227x406','','','40071429','');
INSERT INTO "Account" VALUES('Account-24','Montoya, Wells and Daniels','Adaptive system-worthy installation','','','','','','','','','','','','219.441.4029','','','11912061','');
INSERT INTO "Account" VALUES('Account-25','Maldonado, Jones and Moore','Synergized responsive matrix','','','','','','','','','','','','2531039427','','','42328240','');


INSERT INTO "Contact" VALUES('Contact-4','Jacqueline','Brown','Mr.','christopher85@yahoo.com','(951)175-2430x21575','1256216622','Doctor, general practice','1967-05-08','Account-7');
INSERT INTO "Contact" VALUES('Contact-5','Robert','Smith','Ms.','bwilkerson@hunt.org','(954)436-8286x4149','(838)557-1881','Research scientist (life sciences)','1993-06-29','Account-20');
INSERT INTO "Contact" VALUES('Contact-6','Hannah','Duncan','Mr.','williamyoung@suarez.com','118-444-0564','360.346.8024','Nurse, adult','1981-07-26','Account-17');
INSERT INTO "Contact" VALUES('Contact-7','Caitlin','Le','Mx.','jasonryan@foster-johnson.com','+1-889-214-3418x10487','906.009.5203','Designer, furniture','1974-02-26','Account-5');
INSERT INTO "Contact" VALUES('Contact-8','Matthew','Fisher','Mr.','charlesjackson@gmail.com','712-329-6696x327','398.459.0661x7802','Chief Executive Officer','1966-08-01','Account-18');
INSERT INTO "Contact" VALUES('Contact-9','Glenda','Kline','Mx.','olee@hotmail.com','+1-810-820-7245x408','550-664-6651x44430','Chiropractor','1981-04-29','Account-5');
INSERT INTO "Contact" VALUES('Contact-10','Joyce','Anderson','Mr.','brownchristina@gmail.com','502.563.7470','864-440-8796x404','Bonds trader','1978-01-14','Account-15');
INSERT INTO "Contact" VALUES('Contact-11','Leslie','Bennett','Mx.','doliver@dickerson.com','001-012-634-9713x009','001-110-127-0838x1754','Materials engineer','1998-05-29','Account-11');
INSERT INTO "Contact" VALUES('Contact-12','Steven','Butler','Mx.','tgibson@yahoo.com','982.806.0149x61369','500.073.7758x029','Clinical scientist, histocompatibility and immunogenetics','1964-02-08','Account-11');
INSERT INTO "Contact" VALUES('Contact-13','Tami','Thompson','Mx.','amber76@beck.com','(134)982-1925','8011741195','Runner, broadcasting/film/video','1997-01-20','Account-5');
INSERT INTO "Contact" VALUES('Contact-14','Whitney','Fowler','Mx.','calvin49@black-wilson.com','5321396442','+1-739-600-7853x706','Communications engineer','1967-03-13','Account-9');
INSERT INTO "Contact" VALUES('Contact-15','Joe','Rodriguez','Ind.','deborahstokes@yang.net','+1-797-865-4753x485','9915119043','Surveyor, minerals','1970-11-03','Account-1');
INSERT INTO "Contact" VALUES('Contact-16','Carrie','Velasquez','Dr.','kelsey77@campbell.com','(329)100-2219x4869','(662)137-8951x4099','Chartered accountant','1967-12-08','Account-8');
INSERT INTO "Contact" VALUES('Contact-17','Daniel','Gonzalez','Mrs.','ozimmerman@ward.com','494-844-9534x51762','282.514.7235x0060','Adult guidance worker','1980-04-07','Account-16');
INSERT INTO "Contact" VALUES('Contact-18','Christian','Anderson','Mr.','bryanhiggins@johnson.net','001-768-964-7201x37163','+1-311-941-9226x545','Engineer, communications','1996-02-20','Account-19');
INSERT INTO "Contact" VALUES('Contact-19','John','Reed','Mrs.','bradyrebecca@hudson-kelly.net','506.674.3181x77646','(193)410-6407x3228','Medical technical officer','1990-07-01','Account-15');
INSERT INTO "Contact" VALUES('Contact-20','Amy','Smith','Dr.','robert58@quinn.com','001-471-180-1138x505','385-091-1669','Cabin crew','1972-07-08','Account-12');
INSERT INTO "Contact" VALUES('Contact-21','Autumn','Murillo','Mr.','escobarjoshua@hotmail.com','0065834869','(033)013-5568x40028','Chartered legal executive (England and Wales)','1981-02-23','Account-6');
INSERT INTO "Contact" VALUES('Contact-22','Cody','Hernandez','Misc.','malonejonathon@griffin-osborn.com','264-563-2199','908.076.5654x36421','Geologist, engineering','1988-06-03','Account-16');
INSERT INTO "Contact" VALUES('Contact-23','Tyler','Bowers','Dr.','mark64@schultz-parker.net','+1-379-918-6249x6802','989-539-8926x76535','Sport and exercise psychologist','1982-12-02','Account-9');
INSERT INTO "Contact" VALUES('Contact-24','Diana','Ryan','Mr.','kkidd@hotmail.com','356-330-4972x9013','(042)287-4061','Electrical engineer','1976-10-16','Account-11');
INSERT INTO "Contact" VALUES('Contact-25','Jose','Novak','Miss','scurtis@hotmail.com','264-848-6378','2925896479','Geologist, engineering','1976-10-04','Account-12');
INSERT INTO "Contact" VALUES('Contact-26','Maria','Weeks','Mr.','collinsjeffrey@olson.org','852.269.5714x2190','388.255.0264','Chartered legal executive (England and Wales)','1983-03-27','Account-13');
INSERT INTO "Contact" VALUES('Contact-27','Christian','Boyd','Mx.','lgrant@yahoo.com','723.439.3183x41413','(483)287-2534x701','Production assistant, television','1979-12-17','Account-5');
INSERT INTO "Contact" VALUES('Contact-28','Heidi','Huffman','Mr.','marcus29@franklin.com','001-397-797-9946x64647','815.662.3992x42610','Hospital doctor','1995-12-11','Account-16');
INSERT INTO "Contact" VALUES('Contact-29','Lisa','Peck','Mr.','dbradford@christensen.info','(174)433-5387x4278','+1-817-361-3752x5011','Land/geomatics surveyor','1981-11-12','Account-10');
INSERT INTO "Contact" VALUES('Contact-30','James','Evans','Dr.','kennedykim@foster.com','(836)722-6575x49179','(237)846-8347x4073','Musician','1980-01-26','Account-3');
INSERT INTO "Contact" VALUES('Contact-31','Karen','Reilly','Mr.','paulterrell@hotmail.com','(809)024-0484x252','(662)455-4993x582','Biochemist, clinical','1955-03-07','Account-19');
INSERT INTO "Contact" VALUES('Contact-32','Daniel','Gonzales','Mrs.','kent84@hotmail.com','907-045-5503x44414','859-011-9999','Community pharmacist','1979-03-18','Account-1');
INSERT INTO "Contact" VALUES('Contact-33','Debbie','Davis','Mx.','audrey99@hotmail.com','+1-527-014-2246','+1-306-189-2702x4777','Armed forces operational officer','1981-09-15','Account-11');
INSERT INTO "Contact" VALUES('Contact-34','Heidi','Smith','Mx.','jenniferpugh@gmail.com','8265960475','+1-291-670-9597x70096','Site engineer','1979-08-31','Account-3');
INSERT INTO "Contact" VALUES('Contact-35','David','Huff','Dr.','warneremma@hotmail.com','001-108-842-7600','572-083-2511','Aeronautical engineer','2001-09-09','Account-17');
INSERT INTO "Contact" VALUES('Contact-36','Anthony','Thompson','Mr.','johnrandolph@hotmail.com','(722)319-8352x19507','(984)646-1878x893','Energy engineer','1987-04-12','Account-16');
INSERT INTO "Contact" VALUES('Contact-37','Brianna','Flores','Mr.','guerrerojohn@hotmail.com','(040)934-1423x458','005.356.8723','Journalist, newspaper','1962-03-14','Account-8');
INSERT INTO "Contact" VALUES('Contact-38','Nathan','Alexander','Dr.','mccoylarry@duncan.info','200-374-4142x7395','(821)164-0381x13162','Scientist, clinical (histocompatibility and immunogenetics)','1991-08-11','Account-3');
INSERT INTO "Contact" VALUES('Contact-39','Patty','Savage','Mx.','sandersstephen@hotmail.com','(112)877-0657x2996','001-407-135-9742x6586','Education officer, environmental','1988-09-07','Account-5');
INSERT INTO "Contact" VALUES('Contact-40','Timothy','Hendrix','Mr.','jamesthomas@melendez.org','(930)747-5122x43545','326-032-4776','Maintenance engineer','1980-12-31','Account-13');
INSERT INTO "Contact" VALUES('Contact-41','Mathew','Welch','Dr.','brandypatterson@mitchell.com','(372)821-0121','394-174-6163x14401','Doctor, hospital','1985-07-22','Account-9');
INSERT INTO "Contact" VALUES('Contact-42','Rebecca','Lopez','Mr.','geoffrey12@haynes.com','(739)509-2550x56354','027-930-6580x6108','Engineer, building services','1976-07-15','Account-12');
INSERT INTO "Contact" VALUES('Contact-43','Juan','Martinez','Mr.','rmyers@foster.com','410-301-1405','+1-679-823-1570','Economist','1991-08-15','Account-3');
INSERT INTO "Contact" VALUES('Contact-44','Kimberly','Anderson','Mr.','brush@reid-allen.org','039.174.2088x15156','+1-926-533-8571x9711','Applications developer','2002-06-07','Account-19');
INSERT INTO "Contact" VALUES('Contact-45','Steven','Johnson','Mx.','kristenlove@graham.com','323-478-6250x512','(913)638-0634x71085','Plant breeder/geneticist','1985-08-17','Account-13');
INSERT INTO "Contact" VALUES('Contact-46','Diane','Castro','Mr.','jenniferespinoza@yahoo.com','(888)427-7854x17261','(343)337-0016x24802','Counsellor','2001-02-11','Account-2');
INSERT INTO "Contact" VALUES('Contact-47','Kevin','Johnson','Mr.','lejuan@smith.com','(256)300-0666x3076','001-862-940-5100','Psychologist, clinical','1987-06-04','Account-20');
INSERT INTO "Contact" VALUES('Contact-48','Amanda','Davis','Dr.','wileymary@yahoo.com','(480)208-9142','653.024.9216x56380','International aid/development worker','1977-08-22','Account-18');
INSERT INTO "Contact" VALUES('Contact-49','Maria','Jimenez','Mr.','ljones@maldonado-hicks.org','+1-508-122-8616','7616362966','Accountant, chartered certified','1966-01-22','Account-13');
INSERT INTO "Contact" VALUES('Contact-50','Patrick','Mccoy','Mrs.','mariajoseph@hotmail.com','(659)725-4524','962.156.1663','Catering manager','1961-01-01','Account-16');
INSERT INTO "Contact" VALUES('Contact-51','Kristen','Suarez','Mx.','christina51@gmail.com','001-411-577-2094x758','889-250-7752','Chartered legal executive (England and Wales)','1994-06-23','Account-15');
INSERT INTO "Contact" VALUES('Contact-52','Debbie','Alvarez','Mx.','tammymedina@hotmail.com','001-086-686-9414x15115','012-043-1931','Loss adjuster, chartered','1964-11-08','Account-13');
INSERT INTO "Contact" VALUES('Contact-53','Traci','Banks','Dr.','tiffany64@gmail.com','308-249-7490','+1-583-349-6177x858','Librarian, academic','1967-02-27','Account-15');
INSERT INTO "Contact" VALUES('Contact-54','Eric','Johnson','Mx.','aharris@cunningham.com','(102)107-1088','001-821-976-9439x923','Teacher, primary school','1992-07-09','Account-6');
INSERT INTO "Contact" VALUES('Contact-55','Shawn','Diaz','Dr.','hochoa@martin.com','2335286273','+1-138-151-5601x23752','Sub','1962-09-10','Account-7');
INSERT INTO "Contact" VALUES('Contact-56','Cynthia','Carroll','Dr.','jonathan75@espinoza.com','909-941-2179x15747','972-747-7021x87437','Volunteer coordinator','2001-04-26','Account-15');
INSERT INTO "Contact" VALUES('Contact-57','Derek','English','Mr.','figueroalinda@larson.com','771-805-6663x3500','(929)813-8603x896','Acupuncturist','1956-03-02','Account-4');
INSERT INTO "Contact" VALUES('Contact-58','Dean','Ortiz','Mr.','jonathan33@yahoo.com','286.477.8501x77097','335.033.8461x92224','Podiatrist','1969-01-28','Account-1');
INSERT INTO "Contact" VALUES('Contact-59','Thomas','Watson','Mrs.','wrobertson@adams.com','+1-044-359-5440x3220','5242854984','Visual merchandiser','1977-05-17','Account-1');
INSERT INTO "Contact" VALUES('Contact-60','Lynn','Frey','Mrs.','olivia38@schaefer.com','001-876-374-1841x70622','158.527.9951x1108','Operational researcher','1965-07-01','Account-3');
INSERT INTO "Contact" VALUES('Contact-61','Jonathan','Steele','Dr.','brandon28@fields.com','001-645-936-4973x340','686.831.0030','Quarry manager','1972-06-09','Account-19');
INSERT INTO "Contact" VALUES('Contact-62','Teresa','Williams','Dr.','yhood@cooper.com','(600)862-5939x599','001-262-786-9797','Equality and diversity officer','1967-07-10','Account-1');
INSERT INTO "Contact" VALUES('Contact-63','Sandra','Henderson','Ms.','smithmichael@yahoo.com','001-059-111-8601x187','5057044225','Logistics and distribution manager','1961-11-07','Account-9');
INSERT INTO "Contact" VALUES('Contact-64','Darrell','Stone','Mrs.','thomasmichelle@woods-tyler.com','(575)527-9862x16794','075.950.5314','Radiation protection practitioner','2003-07-07','Account-12');
INSERT INTO "Contact" VALUES('Contact-65','Christopher','Stephens','Dr.','katrina23@gmail.com','(184)173-5357x5740','960.937.4682','Designer, fashion/clothing','1967-12-14','Account-4');
INSERT INTO "Contact" VALUES('Contact-66','Jonathan','Sanders','Mr.','walkerethan@gmail.com','+1-288-991-4519x454','001-013-648-7553','Scientist, forensic','1970-05-04','Account-3');
INSERT INTO "Contact" VALUES('Contact-67','Debra','Rodriguez','Ind.','sampsonamy@gmail.com','+1-570-020-1500x07002','800-841-6902x384','Administrator','1971-11-25','Account-8');
INSERT INTO "Contact" VALUES('Contact-68','Barbara','Bates','Mx.','watsonbrandon@carpenter.org','(125)608-9445x280','001-352-204-9634x767','Aid worker','1974-12-24','Account-8');
INSERT INTO "Contact" VALUES('Contact-69','Jerry','Davis','Dr.','umcfarland@hotmail.com','(944)188-4914','271.688.9384','Dietitian','1997-09-11','Account-6');
INSERT INTO "Contact" VALUES('Contact-70','Eric','Turner','Dr.','kimberly51@massey-taylor.com','175.696.6542','+1-178-116-3595x475','Orthoptist','1959-12-03','Account-17');
INSERT INTO "Contact" VALUES('Contact-71','Joanna','Benton','Dr.','lnash@hotmail.com','838.192.6818','020.272.6352','Therapist, horticultural','1986-04-09','Account-13');
INSERT INTO "Contact" VALUES('Contact-72','Christopher','Stevens','Dr.','simpsonbilly@hotmail.com','038.162.8486x906','309-250-0812x3139','Clinical psychologist','1954-08-11','Account-18');
INSERT INTO "Contact" VALUES('Contact-73','Erin','Barron','Mr.','robertjarvis@reed-johnson.com','7606999523','6153409570','Risk manager','1968-10-18','Account-19');
INSERT INTO "Contact" VALUES('Contact-74','Wayne','Shelton','Dr.','leslie07@hotmail.com','(745)348-2609x0182','122-476-1588x59819','Dance movement psychotherapist','1975-05-27','Account-12');
INSERT INTO "Contact" VALUES('Contact-75','Jessica','Hardy','Mx.','krollins@gmail.com','507.507.0232x57702','703.252.9694x28556','Surveyor, land/geomatics','1988-10-08','Account-10');
INSERT INTO "Contact" VALUES('Contact-76','Ashley','Robinson','Miss','kimberly63@gmail.com','+1-033-702-4232x7829','001-029-710-7322','Sports coach','1970-10-15','Account-15');
INSERT INTO "Contact" VALUES('Contact-77','Christina','Brooks','Dr.','ltaylor@hughes.info','(721)750-8969','(958)358-6059','Investment banker, corporate','1976-08-04','Account-16');
INSERT INTO "Contact" VALUES('Contact-78','Anna','Glass','Mr.','ocardenas@hampton.com','(646)907-5188x343','314-776-3643x168','Chief Financial Officer','1958-01-02','Account-1');
INSERT INTO "Contact" VALUES('Contact-79','Kimberly','Navarro','Ms.','adamslinda@smith.biz','001-914-318-0025x483','(484)635-0527x97649','Health promotion specialist','1958-03-09','Account-8');
INSERT INTO "Contact" VALUES('Contact-80','Zachary','Hale','Mx.','jaredchristian@rogers.com','412-286-3270','001-749-000-1081x6632','Aeronautical engineer','1966-03-04','Account-16');
INSERT INTO "Contact" VALUES('Contact-81','Jeffrey','Patterson','Mrs.','michael14@gmail.com','+1-971-161-3494x40567','322.869.0877x4269','Chartered loss adjuster','1997-12-30','Account-12');
INSERT INTO "Contact" VALUES('Contact-82','Ashlee','Douglas','Dr.','ljohnson@yahoo.com','(107)073-2864x709','+1-543-955-1348x27165','Media buyer','1975-11-24','Account-1');
INSERT INTO "Contact" VALUES('Contact-83','Amy','Jackson','Ms.','jbrown@yahoo.com','(656)107-4242','(300)274-8183x877','Radiographer, therapeutic','1977-05-04','Account-20');
INSERT INTO "Contact" VALUES('Contact-84','Austin','Arnold','Mrs.','aevans@thompson.org','702.321.9550x57620','563.499.1591','Customer service manager','1965-04-23','Account-5');
INSERT INTO "Contact" VALUES('Contact-85','Lisa','Hahn','Mrs.','pamelathomas@davis-mills.com','563.647.1985','516-184-8784x18409','Psychotherapist','1982-03-11','Account-9');
INSERT INTO "Contact" VALUES('Contact-86','Michael','Rice','Mrs.','wwalker@gmail.com','136-191-2472','(012)569-2985x7448','Education administrator','1964-07-14','Account-7');
INSERT INTO "Contact" VALUES('Contact-87','Judith','Ross','Mrs.','karen84@cook.com','001-896-116-2678','+1-591-808-0731x50857','Comptroller','1962-09-04','Account-7');
INSERT INTO "Contact" VALUES('Contact-88','Debbie','Hooper','Ind.','james11@davis.com','319-281-3272x823','(066)287-5057x484','Probation officer','1965-09-09','Account-7');
INSERT INTO "Contact" VALUES('Contact-89','Luis','Smith','Mrs.','yallen@becker-hunt.net','001-427-071-0883x18715','+1-776-803-7761','Manufacturing engineer','1990-07-14','Account-14');
INSERT INTO "Contact" VALUES('Contact-90','Peter','Anderson','Dr.','allentyler@guzman.org','+1-393-254-9105x178','676.588.9551x635','Administrator, Civil Service','1967-07-06','Account-12');
INSERT INTO "Contact" VALUES('Contact-91','John','Ward','Mr.','karlamarquez@orr.com','551.753.6658x8830','001-235-880-4273x489','Contracting civil engineer','1966-07-07','Account-17');
INSERT INTO "Contact" VALUES('Contact-92','Susan','Colon','Mrs.','jerrywalker@knox.com','2886198694','139-647-8366x467','Warden/ranger','1961-08-17','Account-12');
INSERT INTO "Contact" VALUES('Contact-93','Julie','Higgins','Dr.','curtis88@hotmail.com','856.472.4550','(436)489-2153','Passenger transport manager','1962-11-18','Account-4');
INSERT INTO "Contact" VALUES('Contact-94','Allen','Robinson','Dr.','alexander94@ortega.com','901.887.7671x4722','7628475086','Biochemist, clinical','1980-06-29','Account-1');
INSERT INTO "Contact" VALUES('Contact-95','Nathan','Yoder','Misc.','watsonmichael@wilson-benson.com','(799)922-5588','(943)647-6987x45290','Paramedic','1961-09-02','Account-3');
INSERT INTO "Contact" VALUES('Contact-96','Sheryl','Mckee','Mr.','michael29@gmail.com','2373626803','4779103743','Furniture designer','1960-03-18','Account-3');
INSERT INTO "Contact" VALUES('Contact-97','Melissa','Browning','Mrs.','daniel78@burns.org','001-910-900-7974','(293)760-7748','Quantity surveyor','1956-04-28','Account-20');
INSERT INTO "Contact" VALUES('Contact-98','Elizabeth','Preston','Mrs.','roberttaylor@gmail.com','+1-367-895-8706x8070','001-083-228-6710x5234','Media buyer','1993-06-02','Account-6');
INSERT INTO "Contact" VALUES('Contact-99','Karen','Goodwin','Mr.','stephen15@barber-perkins.com','640-922-2069x071','001-340-296-7013x02254','Therapist, art','1979-01-20','Account-9');
INSERT INTO "Contact" VALUES('Contact-100','Chase','Wilson','Dr.','mdonaldson@gmail.com','(835)291-0076x88366','8748248647','Therapist, sports','1994-10-06','Account-17');
COMMIT;
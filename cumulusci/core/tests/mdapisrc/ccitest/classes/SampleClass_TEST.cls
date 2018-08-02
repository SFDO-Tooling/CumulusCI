@isTest
public with sharing class SampleClass_TEST {

    public static testmethod void fillInFirstNameTest() {
    	SampleClass myClass = new SampleClass();
    	Contact contact = new Contact(LastName = 'Testerson');
		Test.startTest();
    	insert contact;
    	myClass.fillInFirstName(new Contact[]{contact});
    	update contact;
		Test.stopTest();
    	contact = [select FirstName from Contact where Id = :contact.Id];
    	System.assertEquals('Test', contact.FirstName);
	delete contact;
    }
}

public with sharing class SampleClass {

    /** Sample method that will populate a contact's first name if empty. **/
    public void fillInFirstName(List<Contact> contacts) {
    	List<Contact> contactsToUpdate = new List<Contact>();
    	for(Contact contact : contacts) {
    		if(String.isBlank(contact.FirstName)) {
    			contact.FirstName = 'Test';
    			contactsToUpdate.add(contact);
    		}
    	}
    }
}
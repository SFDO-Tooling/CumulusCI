public with sharing class SamplePage_CTRL {

    public List<SampleObject__c> getSamples() {
    	return [select Sample_Field__c from SampleObject__c];
    }
}
trigger SampleTrigger on Contact (before insert, before update) {

    SampleClass myClass = new SampleClass();
    myClass.fillInFirstName(Trigger.new);
}
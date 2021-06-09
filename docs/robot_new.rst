===============
Robot Framework
===============

Robot Framework (or simply "robot") is a keyword-driven acceptance testing framework used by CumulusCI. *Keyword-driven* means that test cases are made up of high-level keywords that allow acceptance tests to be written in an intuitive, human-readable language ("Open browser", "Click link", "Insert text") rather than in a programming language. *Acceptance testing* requires that a project being developed works from, and meets the needs of, a user's (or client's) perspective before being pushed into production. 

This document provides details about CumulusCI's integration with `Robot Framework <http://robotframework.org>`_ for automating tests using CumulusCI, Salesforce APIs, and Selenium, and how to get the most out of Robot through the adoption of *foundation tests*.



The Foundation Test
-------------------

When it comes to testing, we like to encourage a new best practice: the foundation test. A foundation test takes the approach that testing should focus on Quality *Assistance*, a process that begins early in development, ideally in conjuction with the *first task of the first sprint* of writing code, versus Quality Assurance, which usually comes at the end of production, when it can be more difficult to suss out and fix deep-rooted errors and bugs, and almost as an afterthought in the project design.

A foundation test is an automated `happy path <https://en.wikipedia.org/wiki/Happy_path>`_ test written very early in a project, and serves as a living document over the course of the project. Simply, foundation tests:

* Clarify for the entire team what kind of user experience a customer will have from start to finish
* Are written via collaboration with the team, throughout development, not solely by quality engineers at the end
* Provide a road map for keyword development, which helps the team prioritize what keywords need to be created for the project
* Are a useful tool to bring new team members, or even someone not wholly familiar with web development, up to speed with the project

For example, let's say you're building an appointment manager for a student advisor scheduling time with their students. By collaborating with the product owner, even with a rough outline you know a few actions that an advisor must be able to do through the appointment manager.

* Open and close the appointment manager.
* See a list of all today’s appointments.
* Create a new appointment for a student.
* Create a new walk-in appointment.

By writing tests that cover these simple scenarios, you build a *foundation* upon which you can build all of the other tests. So if you write a test to create a new appointment, you can use the keywords from that test to write a new test that shows the list of today's appointments, and so on.

.. comments
   To read more on foundation tests, see the documentation here.
   IS THERE A CHANCE OF MAKING THE CONFLUENCE PAGE PUBLIC?



Why Robot?
----------

What makes Robot Framework an ideal acceptance testing framework for Salesforce?

* Human readable test cases: Robot uses *domain-specific language*, or DSL, for testing in browser. DSLs take complex arguments for functions and present them in a more simplistic programming language. So instead of writing elaborate code for your Robot test cases, you use basic, digestible keywords that don't require code syntax or functions.
* Libraries provide keywords: Salesforce has a comprehensive standard library of Robot keywords created specifically to anticipate the needs of testers.
* Test cases use keywords: Robot helps circumvent the actual writing of code (or, more accurately, writing as much code as previously required) by instead relying on keywords.

Example #1: Open Test Browser

Let's start with one of the easiest Robot tests: opening a browser.

.. comment
   Insert code for Open Test Browser here. Afterward, I will walk user through how to store the file and run the test.

Because of these features, Robot offers a better experience with acceptance testing than the previous Salesforce testing hierarchy of Apex, JEST and Integration (API & Browser). Here's why:

* Apex is a programming language developed by Salesforce. Although it offers flexibility with building apps from scratch, it is inefficient for acceptance testing framework due to its complex code and complicated commands.
* JEST is a testing framework written in JavaScript, but it doesn't offer a lot of flexibility in its test cases, instead being used primarily for browser automation, which automates tests to run across any number of browsers to more efficiently find bugs, and to ensure a consistent user experience.
* Integration testing covers everything from low-level unit tests, which test specific (and often basic) methods in your code such as addition or subtraction, to UI tests that run a comprehensive testing sequence to find possible bugs. Traditional integration tests are great from a technical perspective, but they aren't as expressive or as relatable to high-level, user-centric tests as Robot. 

Most modern browser automation is done with Selenium, which Robot uses to bridge the gap between low-level and high-level tests. In this way Robot becomes a dynamic acceptance testing framework that uses simple keywords to run automated tests.



A More Efficient Robot
----------------------

We encourage foundation testing as a means to maximize the efficiency of Robot tests with CumulusCI. If your Robot tests are written and run *alongside* your project's development, not only does it reduce errors during the development process, it also gives your team a clear outline on what code and keywords need to be written each step of the way.

And because testing is sometimes a secondary concern for development teams, this Robot documentation is written with that in mind. Ahead are neatly explained examples of Robot tests that leverage the features of CumulusCI, each one written as a foundation test to be run during development, not after.

The goal here is to demystify the testing process for everyone who works with CumulusCI, to give a head start on designing essential Robot tests, and to inspire you to build upon the test cases given here to meet the needs of your project. 

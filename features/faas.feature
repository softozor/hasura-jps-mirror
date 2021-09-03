# TODO: install the faas engine once and for all for the whole feature
Feature: The faas engine

  The faas engine will allow to bind hasura actions and
  events to functions.

  Background: Docker node is available

    Given a jelastic environment with 1 docker node is available in group 'faas' with image 'softozor/ubuntu-git:latest'
    And the faas engine is installed

  Scenario: Log on

    When a user logs on the faas engine
    Then she gets a success response

  Scenario: Deploy new function

    Given a user is logged on the faas engine
    When she deploys the 'hello-python' function to the faas engine
    Then she gets a success response

  Scenario: Call function

    Given the 'hello-python' function has been deployed on the faas engine
    When a user invokes it with payload 'it is me'
    Then she gets http status 200
    And she gets content
      """
      Hello! You said: it is me

      """
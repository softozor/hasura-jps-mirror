# TODO: install the main manifest before the whole feature
Feature: Hasura API

  As a user,
  I want to use the hasura API,
  in order to build my system.

  Background: The main manifest is installed

    Given the user has installed the main manifest

  Scenario: The faas engine is well-defined

    Then there is 1 docker node in the faas node group

  Scenario: The database is deployed in a master-slave architecture

    Then there are 2 postgres13 nodes in the sqldb node group  

  Scenario: The api is deployed in the cp node group

    Then there is 1 docker node in the cp node group

  Scenario: A load balancer is served in front of the compute node

    Then there is 1 nginx-dockerized node in the bl node group

  # TODO: check that the nginx has ssl installed

  Scenario: Hasura accepts database migrations

    When the user applies the database migrations of the 'todo_project'
    Then she gets success

  Scenario: The hasura API is functional

    Given the user has applied the database migrations of the 'todo_project'
    And its database metadata
    And she has added a todo through the following graphql mutation
    """
    mutation {
      insert_todos_one(object: {
        title: "make hasura work"
        description: "we need a jelastic manifest to install hasura"
      }) {
        id
      }
    }
    """
    When she retrieves the new todo with the following query
    """
    query GetTodo ($id: uuid!) {
      todos_by_pk (id: $id) {
        description
        state
      }
    }
    """
    Then she gets the description
    """
    we need a jelastic manifest to install hasura
    """
    And state 'NEW'

  Scenario: The faas engine integrates with hasura API

    Given the 'hasura-action' function has been deployed on the faas engine
    And the user has applied the database migrations of the 'todo_project'
    And its database metadata
    And she has added a todo through the following graphql mutation
    """
    mutation {
      insert_todos_one(object: {
        title: "make hasura work"
        description: "we need a jelastic manifest to install hasura"
      }) {
        id
      }
    }
    """
    And the user has started the todo with the hasura action
    """
    mutation Do ($id: uuid!) {
      do(id: $id) {
        state
      }
    }
    """
    When she retrieves the new todo with the following query
    """
    query GetTodo ($id: uuid!) {
      todos_by_pk (id: $id) {
        state
      }
    }
    """
    Then she gets state 'DOING'

  # TODO: try to log on as a user with some permissions and call a mutation requiring that permission (e.g. delete todo)
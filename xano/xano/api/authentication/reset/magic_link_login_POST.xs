// Exchanges magic token for auth token. Logs in user with the one-time link.
query "reset/magic-link-login" verb=POST {
  api_group = "Authentication"

  input {
    text magic_token? filters=trim
    text email? filters=trim
  }

  stack {
    // Check to make sure the magic token exists
    precondition ($input.magic_token != null) {
      error = "magic_token is required but was not provided."
    }
  
    // Check to make sure the email exists
    precondition ($input.email != null) {
      error = "email is required but not provided"
    }
  
    db.transaction {
      stack {
        db.get user {
          field_name = "email"
          field_value = $input.email
          output = [
            "id"
            "created_at"
            "name"
            "email"
            "role"
            "password_reset.token"
            "password_reset.expiration"
            "password_reset.used"
          ]
        } as $user

        precondition ($user != null) {
          error_type = "unauthorized"
          error = "The token is invalid or expired."
        }

        security.check_password {
          text_password = $input.magic_token
          hash_password = $user.password_reset.token
        } as $verify_token

        precondition ($verify_token) {
          error_type = "unauthorized"
          error = "The token is invalid or expired."
        }

        precondition ($user.password_reset.expiration > now) {
          error_type = "unauthorized"
          error = "The token is invalid or expired."
        }

        precondition ($user.password_reset.used == false) {
          error_type = "unauthorized"
          error = "The token is invalid or expired."
        }

        db.edit user {
          field_name = "id"
          field_value = $user.id
          data = {
            password_reset: {
              token     : $user.password_reset.token
              expiration: $user.password_reset.expiration
              used      : true
            }
          }
        } as $user1
      }
    }

    security.create_auth_token {
      table = "user"
      extras = ""
      expiration = 86400
      id = $user.id
    } as $auth_token
  
    // Create an event log for password reset login
    function.run "Quick Start/log_event" {
      input = {
        user_id: $user.id
        action : "login_for_password_reset"
        result : "success"
      }
    } as $event_log
  }

  response = {authToken: $auth_token, user_id: $user1.id}
  tags = ["xano:quick-start"]
  guid = "8IKNweo-zxAND1vLU4wUxbUge84"
}
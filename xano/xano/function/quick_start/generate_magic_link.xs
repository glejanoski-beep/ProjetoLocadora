// This function generates a magic token with a 60 minute expiration date.
function "Quick Start/generate_magic_link" {
  input {
    email email?
  }

  stack {
    precondition ($input.email != null) {
      error = "email is required but was not suppiled. "
    }
  
    // Gets the user record by email
    db.query user {
      where = $db.user.email == $input.email
      return = {type: "single"}
    } as $user
  
    var $token {
      value = null
    }

    var $user_email {
      value = null
    }

    conditional {
      if ($user != null) {
        security.create_uuid as $new_token

        var $password_reset {
          value = {}
            |set:"token":$new_token
            |set:"expiration":(now
              |add_secs_to_timestamp:(3600|to_int)
            )
            |set:"used":false
        }

        db.edit user {
          field_name = "id"
          field_value = $user|get:"id":0
          data = {password_reset: $password_reset}
        } as $updated_password_reset

        var.update $token {
          value = $new_token
        }

        var.update $user_email {
          value = $user|get:"email":""
        }
      }
    }
  }

  response = {token: $token, email: $user_email}
  tags = ["xano:quick-start"]
  guid = "7LLWlSh92T5fSs1g4hl47yfefBQ"
}
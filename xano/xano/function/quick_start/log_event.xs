// Creates a record in the event log table
function "Quick Start/log_event" {
  input {
    int user_id?
    text action
    text result?
    text resource_type?
    int resource_id?
  }

  stack {
    // Add a new user event log entry
    db.add event_log {
      data = {
        created_at: "now"
        user_id   : $input.user_id
        action    : $input.action
        metadata  : {
          result       : $input.result
          resource_type: $input.resource_type
          resource_id  : $input.resource_id
        }
      }
    } as $new_log_entry
  }

  response = null
  tags = ["xano:quick-start"]
  guid = "Q1qHScIFgOhX7r4NN4QbUlCK5ZU"
}
use serde_json::{json, Value};
use std::time::{SystemTime, UNIX_EPOCH};

pub fn submission_blocker() -> Option<&'static str> {
    // Worker 06 has no accepted adapter to the original ControlPlane authority.
    // Neither a healthy daemon nor a self-issued DEV receipt supplies that grant.
    Some("Current Owner, Resource/GAME and Windows worker-role admission is unavailable for this worker route.")
}

pub fn attach(mut capabilities: Value) -> Value {
    let compiled = capabilities["worker_compiled"] == true;
    let healthy = capabilities["worker_ready"] == true;
    let check = |id: &str, status: &str, detail: &str, next: &str| json!({"id":id,"status":status,"detail":detail,"next_step":next});
    capabilities["preflight"] = json!({
        "schema":"OpenRemaster.DevPreflight.v1", "production_go":false,
        "checked_at_ms":SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_millis() as u64,
        "valid_for_ms":30000, "can_submit":false,
        "scope":capabilities["worker_scope"],
        "checks":[
            check("native",if compiled {"PASS"} else {"BLOCKED"},
                if compiled {"Native worker support is compiled."} else {"This portable preview contains the Studio UI."},"Use a commissioned HomePC build for worker integration."),
            check("worker",if healthy {"PASS"} else {"BLOCKED"},
                if healthy {"The pinned worker responds."} else {"The pinned worker is unavailable, stopped or holding."},"Inspect the existing worker and its pinned configuration."),
            check("owner","UNKNOWN","A current operation-bound Owner/writer grant has not been verified.","Obtain fresh readback from the original operator authority."),
            check("resources","UNKNOWN","A current heavy-task reservation has not been verified.","Verify the original Resource Governor reservation for this operation."),
            check("game","UNKNOWN","The original GAME/LIGHT policy has not been verified.","Verify the current GAME mode through the original ControlPlane."),
            check("account","UNKNOWN","The required Windows worker role is not bound to this route.","Verify the original configured worker account; do not change identity in Studio."),
            check("source","UNKNOWN","The worker snapshot and this Git build are separate source scopes.","Bind the approved source, build plan and paired worker through the original procedure.")
        ]
    });
    capabilities
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn portable_healthy_worker_does_not_grant_execution() {
        let value = attach(
            json!({"worker_compiled":true,"worker_ready":true,"worker_scope":"b".repeat(64)}),
        );
        assert_eq!(value["preflight"]["can_submit"], false);
        assert!(submission_blocker().is_some());
        assert_eq!(value["preflight"]["checks"][1]["status"], "PASS");
        assert_eq!(value["preflight"]["checks"][2]["status"], "UNKNOWN");
    }
}

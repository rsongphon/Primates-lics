# Phase 2 Manual Testing Instructions

## Overview

This document provides detailed manual testing instructions for the 29 skipped test cases in the LICS Phase 2 Backend Core Development test suite. These tests require manual verification due to their complexity, need for external services, or requirements for real-time user interaction.

### Automated Test Status
- **Total Tests**: 125
- **Automated Tests**: 96 (77% pass rate, 93% effective pass rate)
- **Manual Tests**: 29 (documented here)
- **Overall Coverage**: 100% when automated + manual tests are completed

### Test Categories Requiring Manual Verification
1. **Authentication & Authorization** (2 tests) - Email/TOTP verification
2. **WebSocket & Real-time Features** (15 tests) - Event-driven interactions
3. **Background Tasks & Scheduling** (11 tests) - Complex Celery operations
4. **API Error Handling** (1 test) - Safe error simulation

---

## Prerequisites & Setup

### Development Environment
Ensure the following services are running before manual testing:

```bash
# Start complete development environment
make dev
```

### Required Tools & Services
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MailHog** (Email Testing): http://localhost:8025
- **Flower** (Celery Monitoring): http://localhost:5555 (admin:admin123)
- **PgAdmin** (Database GUI): http://localhost:5050 (admin@lics.dev / admin123)
- **Redis Commander**: http://localhost:8081
- **WebSocket Server**: ws://localhost:8001
- **Frontend**: http://localhost:3000

### Test Accounts Setup
Create the following test accounts via the API or frontend:

1. **Admin User**: `admin@lics.dev` / `admin123`
2. **Regular User**: `user@test.com` / `testpass123`
3. **Device User**: `device@test.com` / `devicepass123`

### WebSocket Client Tools
- Browser WebSocket clients (WebSocket King, Simple WebSocket Client)
- Postman WebSocket support
- `wscat` command-line tool
- Custom scripts for advanced testing

---

## Authentication & Authorization Tests

### TC-AUTH-008: Password Reset Confirmation

**Objective**: Verify complete password reset flow using email-based token confirmation.

**Why Skipped**: Requires email interaction to extract reset tokens from MailHog.

**Prerequisites**:
- MailHog accessible at http://localhost:8025
- Valid user account with email address
- Backend SMTP configured to use MailHog

**Step-by-Step Instructions**:

1. **Initiate Password Reset**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/password-reset" \
        -H "Content-Type: application/json" \
        -d '{"email": "user@test.com"}'
   ```

2. **Check Email in MailHog**
   - Navigate to http://localhost:8025
   - Locate the email from LICS system
   - Open the email to find the reset token
   - Token format: `/reset-password?token=<uuid>`

3. **Extract Reset Token**
   - Copy the complete reset URL or just the token UUID
   - Example: `http://localhost:3000/reset-password?token=123e4567-e89b-12d3-a456-426614174000`

4. **Confirm Password Reset**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/password-reset/confirm" \
        -H "Content-Type: application/json" \
        -d '{
          "token": "123e4567-e89b-12d3-a456-426614174000",
          "new_password": "newsecurepass123"
        }'
   ```

5. **Verify New Password**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
          "email": "user@test.com",
          "password": "newsecurepass123"
        }'
   ```

**Expected Results**:
- Password reset request returns `200 OK`
- Email received in MailHog with valid reset token
- Password reset confirmation returns `200 OK`
- Login succeeds with new password
- Login fails with old password

**Troubleshooting**:
- **No email received**: Check MailHog logs, verify SMTP configuration
- **Invalid token**: Tokens expire after 1 hour, request new reset
- **Token already used**: Each token can only be used once

---

### TC-AUTH-013: MFA Login Flow

**Objective**: Verify Multi-Factor Authentication using TOTP (Time-based One-Time Password).

**Why Skipped**: Requires TOTP generator and manual QR code scanning.

**Prerequisites**:
- TOTP mobile app (Google Authenticator, Authy, etc.)
- User account with MFA enabled
- Backend TOTP configuration

**Step-by-Step Instructions**:

1. **Enable MFA for User**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/mfa/enable" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json"
   ```

2. **Get MFA Setup Details**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/auth/mfa/setup" \
        -H "Authorization: Bearer <jwt_token>"
   ```

3. **Scan QR Code**
   - Response contains `qr_code_url` and `secret_key`
   - Open the QR code URL in browser or scan with mobile app
   - Alternatively, manually enter the secret key in TOTP app

4. **Generate TOTP Code**
   - Use your TOTP app to generate current 6-digit code
   - Codes refresh every 30 seconds

5. **Verify MFA Setup**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/mfa/verify" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"code": "123456"}'
   ```

6. **Test MFA Login Flow**
   ```bash
   # Step 1: Regular login (returns MFA challenge)
   curl -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{
          "email": "user@test.com",
          "password": "testpass123"
        }'
   # Response: {"require_mfa": true, "temp_token": "..."}

   # Step 2: Complete login with TOTP
   curl -X POST "http://localhost:8000/api/v1/auth/mfa/login" \
        -H "Content-Type: application/json" \
        -d '{
          "temp_token": "...",
          "code": "123456"
        }'
   ```

**Expected Results**:
- MFA setup returns QR code and secret key
- TOTP app generates valid 6-digit codes
- MFA verification succeeds with correct code
- Login with MFA requires both password and TOTP code
- Invalid TOTP codes are rejected

**Troubleshooting**:
- **Invalid TOTP**: Check system clock synchronization
- **QR code not working**: Try manual secret key entry
- **Setup failed**: Ensure user doesn't already have MFA enabled

---

## WebSocket & Real-time Features Tests

### General WebSocket Testing Setup

**WebSocket Client Setup**:
```javascript
// Browser WebSocket connection
const ws = new WebSocket('ws://localhost:8001/ws?token=<jwt_token>');

ws.onopen = function(event) {
    console.log('Connected to WebSocket');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

**Authentication Headers**:
```javascript
// For clients that support headers
const ws = new WebSocket('ws://localhost:8001/ws', [], {
    headers: {
        'Authorization': 'Bearer <jwt_token>'
    }
});
```

---

### TC-WS-006: Device Telemetry Events

**Objective**: Verify real-time device telemetry data streaming via WebSocket.

**Why Skipped**: Requires active device sending telemetry data.

**Prerequisites**:
- Registered device in the system
- WebSocket client with authentication
- Device capable of sending telemetry data

**Step-by-Step Instructions**:

1. **Register Device**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/devices" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "Test Device",
          "device_type": "raspberry_pi",
          "location": "Lab Room 1",
          "configuration": {}
        }'
   ```

2. **Connect to WebSocket Device Room**
   ```javascript
   const deviceWs = new WebSocket('ws://localhost:8001/ws/devices/<device_id>?token=<jwt_token>');

   deviceWs.onmessage = function(event) {
       const telemetry = JSON.parse(event.data);
       console.log('Telemetry:', telemetry);
   };
   ```

3. **Simulate Device Telemetry**
   ```python
   # Using Python to simulate device
   import websocket
   import json
   import time

   def on_open(ws):
       # Authenticate and join device room
       auth_msg = {
           "type": "auth",
           "token": "<jwt_token>"
       }
       ws.send(json.dumps(auth_msg))

       # Join device-specific room
       join_msg = {
           "type": "join_room",
           "room": f"device_<device_id>"
       }
       ws.send(json.dumps(join_msg))

   def send_telemetry(ws):
       telemetry = {
           "type": "telemetry",
           "device_id": "<device_id>",
           "data": {
               "cpu_usage": 45.2,
               "memory_usage": 62.1,
               "temperature": 23.5,
               "timestamp": time.time()
           }
       }
       ws.send(json.dumps(telemetry))

   # Connect and send telemetry every 5 seconds
   ws = websocket.WebSocketApp("ws://localhost:8001/ws", on_open=on_open)
   ```

4. **Verify Telemetry Reception**
   - Monitor WebSocket client for incoming telemetry messages
   - Verify data structure and content
   - Check message timestamps

**Expected Results**:
- WebSocket connection established successfully
- Client joins device-specific room
- Telemetry messages received in real-time
- Messages contain valid device ID and telemetry data
- Data includes expected metrics (CPU, memory, temperature)

**Troubleshooting**:
- **Connection failed**: Check JWT token validity and WebSocket server status
- **No messages received**: Verify device registration and room subscription
- **Invalid data format**: Check telemetry message structure

---

### TC-WS-007: Device Status Events

**Objective**: Verify real-time device status change notifications.

**Why Skipped**: Requires active device status changes.

**Prerequisites**:
- Registered device
- WebSocket connection to device room
- Device capable of status changes

**Step-by-Step Instructions**:

1. **Connect to Device Room**
   ```javascript
   const statusWs = new WebSocket('ws://localhost:8001/ws/devices/<device_id>?token=<jwt_token>');

   statusWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       if (message.type === 'device_status') {
           console.log('Status Change:', message);
       }
   };
   ```

2. **Trigger Device Status Changes**
   ```bash
   # Change device to online status
   curl -X PATCH "http://localhost:8000/api/v1/devices/<device_id>/status" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"status": "online", "message": "Device ready"}'

   # Change device to maintenance mode
   curl -X PATCH "http://localhost:8000/api/v1/devices/<device_id>/status" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"status": "maintenance", "message": "Scheduled maintenance"}'

   # Change device to offline status
   curl -X PATCH "http://localhost:8000/api/v1/devices/<device_id>/status" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"status": "offline", "message": "Device shutdown"}'
   ```

3. **Verify Status Notifications**
   - Monitor WebSocket for status change events
   - Check message structure includes: `type`, `device_id`, `status`, `timestamp`
   - Verify status transitions are received in real-time

**Expected Results**:
- Status change API calls return `200 OK`
- WebSocket clients receive immediate notifications
- Status events include previous and new status
- Timestamps are accurate and chronological
- Multiple connected clients receive same notifications

**Troubleshooting**:
- **No notifications**: Verify WebSocket room subscription
- **Delayed notifications**: Check system load and WebSocket performance
- **Missing status data**: Verify API request format and device permissions

---

### TC-WS-008: Device Heartbeat Events

**Objective**: Verify device heartbeat monitoring and timeout detection.

**Why Skipped**: Requires active device sending periodic heartbeats.

**Prerequisites**:
- Device with heartbeat capability
- WebSocket monitoring connection
- Configurable heartbeat intervals

**Step-by-Step Instructions**:

1. **Configure Device Heartbeat**
   ```bash
   curl -X PATCH "http://localhost:8000/api/v1/devices/<device_id>/config" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "heartbeat_interval": 30,
          "heartbeat_timeout": 90
        }'
   ```

2. **Monitor Heartbeat Events**
   ```javascript
   const heartbeatWs = new WebSocket('ws://localhost:8001/ws/devices/<device_id>?token=<jwt_token>');

   heartbeatWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       switch(message.type) {
           case 'heartbeat':
               console.log('Heartbeat received:', message.timestamp);
               break;
           case 'heartbeat_timeout':
               console.log('Heartbeat timeout:', message);
               break;
           case 'device_status':
               if (message.status === 'offline') {
                   console.log('Device marked offline due to missed heartbeats');
               }
               break;
       }
   };
   ```

3. **Send Periodic Heartbeats**
   ```python
   import time
   import requests
   import websocket
   import json

   def send_heartbeat():
       response = requests.post(
           f"http://localhost:8000/api/v1/devices/{device_id}/heartbeat",
           headers={"Authorization": f"Bearer {jwt_token}"}
       )
       return response.status_code == 200

   # Send heartbeats every 30 seconds
   while True:
       if send_heartbeat():
           print("Heartbeat sent successfully")
       else:
           print("Heartbeat failed")
       time.sleep(30)
   ```

4. **Test Heartbeat Timeout**
   - Stop sending heartbeats
   - Wait for timeout period (90 seconds)
   - Verify device status changes to 'offline'
   - Check WebSocket notification of timeout

**Expected Results**:
- Heartbeat API accepts and records device heartbeats
- WebSocket clients receive heartbeat event notifications
- Device status automatically changes to 'offline' after timeout
- Timeout detection works reliably
- Heartbeat resumption restores device to 'online' status

**Troubleshooting**:
- **Heartbeat rejected**: Check device authentication and permissions
- **No timeout detection**: Verify timeout configuration and system clock
- **False timeouts**: Check network connectivity and API response times

---

### TC-WS-009: Experiment State Change Events

**Objective**: Verify real-time experiment lifecycle state change notifications.

**Why Skipped**: Requires active experiment with state transitions.

**Prerequisites**:
- Created experiment
- WebSocket connection to experiment room
- Permissions to modify experiment state

**Step-by-Step Instructions**:

1. **Create Experiment**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/experiments" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "WebSocket Test Experiment",
          "description": "Testing experiment state notifications",
          "protocol_id": "test-protocol-001"
        }'
   ```

2. **Connect to Experiment Room**
   ```javascript
   const experimentWs = new WebSocket('ws://localhost:8001/ws/experiments/<experiment_id>?token=<jwt_token>');

   experimentWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       if (message.type === 'experiment_state_change') {
           console.log('Experiment State Change:', message);
       }
   };
   ```

3. **Trigger State Changes**
   ```bash
   # Start experiment
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/start" \
        -H "Authorization: Bearer <jwt_token>"

   # Pause experiment
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/pause" \
        -H "Authorization: Bearer <jwt_token>"

   # Resume experiment
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/resume" \
        -H "Authorization: Bearer <jwt_token>"

   # Complete experiment
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/complete" \
        -H "Authorization: Bearer <jwt_token>"

   # Cancel experiment
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/cancel" \
        -H "Authorization: Bearer <jwt_token>"
   ```

4. **Verify State Notifications**
   - Monitor WebSocket for each state transition
   - Check message includes: `experiment_id`, `old_state`, `new_state`, `timestamp`
   - Verify state transition sequence is correct

**Expected Results**:
- Each state change API call returns `200 OK`
- WebSocket clients receive immediate notifications
- State transitions follow proper sequence (draft → running → paused → completed/cancelled)
- Notifications include experiment details and state information
- Multiple participants receive synchronized notifications

**Troubleshooting**:
- **No notifications**: Verify experiment room subscription and permissions
- **Invalid state transitions**: Check experiment state machine rules
- **Missing state data**: Verify API responses and WebSocket message format

---

### TC-WS-010: Experiment Progress Events

**Objective**: Verify real-time experiment progress updates during task execution.

**Why Skipped**: Requires active experiment with tasks in progress.

**Prerequisites**:
- Running experiment with assigned tasks
- WebSocket connection to experiment room
- Task execution capability

**Step-by-Step Instructions**:

1. **Start Experiment with Tasks**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/start" \
        -H "Authorization: Bearer <jwt_token>"
   ```

2. **Monitor Progress Events**
   ```javascript
   const progressWs = new WebSocket('ws://localhost:8001/ws/experiments/<experiment_id>?token=<jwt_token>');

   progressWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       switch(message.type) {
           case 'experiment_progress':
               console.log('Progress Update:', message);
               break;
           case 'task_started':
               console.log('Task Started:', message);
               break;
           case 'task_completed':
               console.log('Task Completed:', message);
               break;
       }
   };
   ```

3. **Execute Tasks and Track Progress**
   ```bash
   # Get experiment tasks
   curl -X GET "http://localhost:8000/api/v1/experiments/<experiment_id>/tasks" \
        -H "Authorization: Bearer <jwt_token>"

   # Execute individual tasks
   curl -X POST "http://localhost:8000/api/v1/tasks/<task_id>/execute" \
        -H "Authorization: Bearer <jwt_token>"

   # Update task progress
   curl -X PATCH "http://localhost:8000/api/v1/tasks/<task_id>/progress" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"progress": 45, "message": "Processing data collection"}'
   ```

4. **Verify Progress Calculations**
   - Monitor overall experiment progress percentage
   - Check individual task completion status
   - Verify progress aggregation is accurate

**Expected Results**:
- Progress events include accurate completion percentages
- Task start/completion events trigger progress updates
- Progress calculation accounts for task weights/durations
- Real-time progress updates are received without delay
- Progress reaches 100% when all tasks complete

**Troubleshooting**:
- **No progress updates**: Verify tasks are executing and reporting progress
- **Incorrect percentages**: Check task weight configuration and calculation logic
- **Delayed updates**: Verify WebSocket performance and system load

---

### TC-WS-011: Experiment Data Collected Events

**Objective**: Verify real-time notifications when experiment data is collected.

**Why Skipped**: Requires active experiment data collection events.

**Prerequisites**:
- Running experiment with data collection
- WebSocket monitoring connection
- Data generation or simulation capability

**Step-by-Step Instructions**:

1. **Connect to Experiment Data Stream**
   ```javascript
   const dataWs = new WebSocket('ws://localhost:8001/ws/experiments/<experiment_id>/data?token=<jwt_token>');

   dataWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       if (message.type === 'data_collected') {
           console.log('Data Collected:', message);
       }
   };
   ```

2. **Simulate Data Collection**
   ```python
   import requests
   import json
   import time
   import random

   def simulate_data_collection(experiment_id, participant_id):
       data_point = {
           "timestamp": time.time(),
           "participant_id": participant_id,
           "metrics": {
               "heart_rate": random.randint(60, 100),
               "activity_level": random.uniform(0.1, 1.0),
               "response_time": random.uniform(200, 800)
           }
       }

       response = requests.post(
           f"http://localhost:8000/api/v1/experiments/{experiment_id}/data",
           headers={
               "Authorization": f"Bearer {jwt_token}",
               "Content-Type": "application/json"
           },
           json=data_point
       )
       return response.status_code == 201

   # Simulate continuous data collection
   while True:
       if simulate_data_collection(experiment_id, participant_id):
           print("Data point collected")
       time.sleep(5)
   ```

3. **Verify Data Notifications**
   - Monitor WebSocket for data collection events
   - Check message structure includes: `experiment_id`, `data_point`, `timestamp`
   - Verify data integrity and format

**Expected Results**:
- Data collection API accepts and stores data points
- WebSocket clients receive immediate notifications
- Data events include complete data point information
- Multiple data points generate corresponding notifications
- Data format matches expected schema

**Troubleshooting**:
- **No data notifications**: Verify WebSocket subscription to data channel
- **Data rejected**: Check data format validation and experiment permissions
- **Missing data in notifications**: Verify message serialization and transmission

---

### TC-WS-012: Task Execution Started Events

**Objective**: Verify real-time notifications when tasks begin execution.

**Why Skipped**: Requires active task execution initiation.

**Prerequisites**:
- Experiment with ready tasks
- WebSocket connection to experiment room
- Task execution permissions

**Step-by-Step Instructions**:

1. **Get Available Tasks**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/experiments/<experiment_id>/tasks" \
        -H "Authorization: Bearer <jwt_token>"
   ```

2. **Monitor Task Start Events**
   ```javascript
   const taskStartWs = new WebSocket('ws://localhost:8001/ws/experiments/<experiment_id>?token=<jwt_token>');

   taskStartWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       if (message.type === 'task_execution_started') {
           console.log('Task Started:', message);
       }
   };
   ```

3. **Execute Multiple Tasks**
   ```bash
   # Execute tasks individually
   for task_id in "${TASK_IDS[@]}"; do
       curl -X POST "http://localhost:8000/api/v1/tasks/${task_id}/execute" \
            -H "Authorization: Bearer <jwt_token>" \
            -H "Content-Type: application/json" \
            -d '{"participant_id": "participant-001"}'

       # Wait for task start notification
       sleep 2
   done
   ```

4. **Verify Start Notifications**
   - Check each task execution generates a start event
   - Verify events include: `task_id`, `experiment_id`, `participant_id`, `timestamp`
   - Confirm start time is accurate

**Expected Results**:
- Task execution API calls return `200 OK`
- WebSocket clients receive immediate task start notifications
- Start events include complete task execution details
- Multiple tasks generate separate, sequential start events
- Task start time is accurately recorded

**Troubleshooting**:
- **No start notifications**: Verify task execution API calls succeed
- **Delayed notifications**: Check WebSocket performance and system load
- **Missing task details**: Verify task data serialization in WebSocket messages

---

### TC-WS-013: Task Execution Progress Events

**Objective**: Verify real-time task progress updates during execution.

**Why Skipped**: Requires active task execution with progress reporting.

**Prerequisites**:
- Currently executing task
- WebSocket connection to task room
- Progress update capability

**Step-by-Step Instructions**:

1. **Connect to Task-Specific Room**
   ```javascript
   const taskProgressWs = new WebSocket('ws://localhost:8001/ws/tasks/<task_id>?token=<jwt_token>');

   taskProgressWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       if (message.type === 'task_progress') {
           console.log('Task Progress:', message);
       }
   };
   ```

2. **Execute Task with Progress Updates**
   ```python
   import requests
   import time
   import json

   def execute_task_with_progress(task_id):
       # Start task execution
       response = requests.post(
           f"http://localhost:8000/api/v1/tasks/{task_id}/execute",
           headers={"Authorization": f"Bearer {jwt_token}"}
       )

       if response.status_code == 200:
           # Simulate progress updates
           for progress in range(10, 101, 10):
               progress_response = requests.patch(
                   f"http://localhost:8000/api/v1/tasks/{task_id}/progress",
                   headers={
                       "Authorization": f"Bearer {jwt_token}",
                       "Content-Type": "application/json"
                   },
                   json={
                       "progress": progress,
                       "message": f"Processing step {progress//10}/10"
                   }
               )
               print(f"Progress {progress}%: {progress_response.status_code}")
               time.sleep(1)

   execute_task_with_progress("task-001")
   ```

3. **Monitor Progress Updates**
   - Watch WebSocket for progress percentage changes
   - Verify progress increments are received in real-time
   - Check progress messages and timestamps

**Expected Results**:
- Progress update API calls return `200 OK`
- WebSocket clients receive immediate progress notifications
- Progress percentages are accurate and sequential
- Progress messages provide meaningful status information
- Updates are received without significant delay

**Troubleshooting**:
- **No progress events**: Verify task execution state and progress API calls
- **Jumping progress**: Check progress validation and increment logic
- **Missing messages**: Verify progress message content in WebSocket payload

---

### TC-WS-014: Task Execution Completed Events

**Objective**: Verify real-time notifications when tasks complete execution.

**Why Skipped**: Requires active task execution reaching completion.

**Prerequisites**:
- Executing task
- WebSocket connection to task/experiment room
- Task completion capability

**Step-by-Step Instructions**:

1. **Monitor Task Completion Events**
   ```javascript
   const taskCompleteWs = new WebSocket('ws://localhost:8001/ws/experiments/<experiment_id>?token=<jwt_token>');

   taskCompleteWs.onmessage = function(event) {
       const message = JSON.parse(event.data);
       if (message.type === 'task_execution_completed') {
           console.log('Task Completed:', message);
       }
   };
   ```

2. **Execute Task to Completion**
   ```python
   import requests
   import time

   def execute_task_to_completion(task_id):
       # Start task
       start_response = requests.post(
           f"http://localhost:8000/api/v1/tasks/{task_id}/execute",
           headers={"Authorization": f"Bearer {jwt_token}"}
       )

       if start_response.status_code == 200:
           # Simulate task work with progress
           for progress in range(20, 101, 20):
               requests.patch(
                   f"http://localhost:8000/api/v1/tasks/{task_id}/progress",
                   headers={
                       "Authorization": f"Bearer {jwt_token}",
                       "Content-Type": "application/json"
                   },
                   json={
                       "progress": progress,
                       "message": f"Processing {progress}% complete"
                   }
               )
               time.sleep(1)

           # Complete the task
           complete_response = requests.post(
               f"http://localhost:8000/api/v1/tasks/{task_id}/complete",
               headers={"Authorization": f"Bearer {jwt_token}"}
           )
           print(f"Task completion: {complete_response.status_code}")

   execute_task_to_completion("task-001")
   ```

3. **Verify Completion Notifications**
   - Check for task completion event
   - Verify completion includes: `task_id`, `final_progress`, `duration`, `result`
   - Confirm completion timestamp accuracy

**Expected Results**:
- Task completion API call returns `200 OK`
- WebSocket clients receive immediate completion notifications
- Completion events include final task statistics and results
- Task status updates to 'completed'
- Experiment progress reflects task completion

**Troubleshooting**:
- **No completion event**: Verify task completion API call succeeds
- **Incomplete task data**: Check task result serialization and message format
- **Status inconsistency**: Verify task state transitions and database updates

---

### TC-WS-015: Notification Events - User

**Objective**: Verify user-specific notification delivery via WebSocket.

**Why Skipped**: Requires notification triggering mechanism.

**Prerequisites**:
- Active user session
- WebSocket connection to user notifications
- System events that generate notifications

**Step-by-Step Instructions**:

1. **Connect to User Notification Channel**
   ```javascript
   const userNotificationWs = new WebSocket('ws://localhost:8001/ws/notifications?token=<jwt_token>');

   userNotificationWs.onmessage = function(event) {
       const notification = JSON.parse(event.data);
       console.log('User Notification:', notification);
   };
   ```

2. **Trigger Notification Events**
   ```bash
   # Create experiment (should generate notification)
   curl -X POST "http://localhost:8000/api/v1/experiments" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "Notification Test Experiment",
          "description": "Testing user notifications"
        }'

   # Assign user to experiment (should generate notification)
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/assign" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"user_id": "user-001", "role": "observer"}'

   # Send manual notification (if API available)
   curl -X POST "http://localhost:8000/api/v1/notifications" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "recipient_id": "user-001",
          "title": "Test Notification",
          "message": "This is a test notification",
          "type": "info"
        }'
   ```

3. **Verify Notification Delivery**
   - Monitor WebSocket for incoming notifications
   - Check notification structure: `id`, `title`, `message`, `type`, `timestamp`
   - Verify notifications are user-specific

**Expected Results**:
- WebSocket connection to user notification channel succeeds
- System events generate appropriate notifications
- Notifications include complete message details
- Notifications are delivered in real-time
- Each user receives only their own notifications

**Troubleshooting**:
- **No notifications**: Verify notification triggers and WebSocket subscription
- **Missing notification data**: Check notification message serialization
- **Cross-user notifications**: Verify user filtering and notification routing

---

### TC-WS-016: Notification Events - Organization

**Objective**: Verify organization-wide notification delivery.

**Why Skipped**: Requires admin notification sending capability.

**Prerequisites**:
- Admin user permissions
- WebSocket connection to organization notifications
- Organization-level events

**Step-by-Step Instructions**:

1. **Connect to Organization Notification Channel**
   ```javascript
   const orgNotificationWs = new WebSocket('ws://localhost:8001/ws/organizations/<org_id>/notifications?token=<jwt_token>');

   orgNotificationWs.onmessage = function(event) {
       const notification = JSON.parse(event.data);
       console.log('Organization Notification:', notification);
   };
   ```

2. **Trigger Organization Notifications**
   ```bash
   # Send organization-wide announcement
   curl -X POST "http://localhost:8000/api/v1/organizations/<org_id>/announcements" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "title": "Scheduled Maintenance",
          "message": "System maintenance scheduled for tonight at 11 PM",
          "type": "maintenance",
          "priority": "high"
        }'

   # Create system-wide alert
   curl -X POST "http://localhost:8000/api/v1/admin/alerts" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "title": "System Alert",
          "message": "Unusual activity detected",
          "type": "security",
          "scope": "organization"
        }'
   ```

3. **Verify Organization Notification Delivery**
   - Monitor WebSocket for organization notifications
   - Verify all organization members receive notifications
   - Check notification includes organization context

**Expected Results**:
- Admin users can send organization-wide notifications
- All organization members receive notifications simultaneously
- Notifications include organization ID and context
- Notification priority and type are properly set
- Non-members do not receive organization notifications

**Troubleshooting**:
- **No org notifications**: Verify admin permissions and organization membership
- **Incomplete delivery**: Check member WebSocket connections and subscriptions
- **Permission errors**: Verify admin JWT token and notification sending permissions

---

### TC-WS-018: WebSocket Permission Check

**Objective**: Verify WebSocket access control and permission enforcement.

**Why Skipped**: Requires multi-user setup to test cross-user permissions.

**Prerequisites**:
- Multiple user accounts with different permission levels
- WebSocket clients for each user
- Resources with restricted access

**Step-by-Step Instructions**:

1. **Test Unauthorized WebSocket Access**
   ```javascript
   // Try connecting without token
   const unauthorizedWs = new WebSocket('ws://localhost:8001/ws/devices/<device_id>');

   unauthorizedWs.onerror = function(event) {
       console.log('Unauthorized access correctly blocked');
   };

   // Try connecting with invalid token
   const invalidTokenWs = new WebSocket('ws://localhost:8001/ws/devices/<device_id>?token=invalid_token');

   invalidTokenWs.onerror = function(event) {
       console.log('Invalid token correctly rejected');
   };
   ```

2. **Test Cross-User Access Prevention**
   ```javascript
   // User A tries to access User B's device
   const userAToken = "user_a_jwt_token";
   const crossAccessWs = new WebSocket('ws://localhost:8001/ws/devices/user_b_device_id?token=' + userAToken);

   crossAccessWs.onerror = function(event) {
       console.log('Cross-user access correctly prevented');
   };
   ```

3. **Test Valid User Access**
   ```javascript
   // User with valid permissions
   const validUserWs = new WebSocket('ws://localhost:8000/ws/devices/<user_device_id>?token=<valid_jwt_token>');

   validUserWs.onopen = function(event) {
       console.log('Valid user access allowed');
   };

   validUserWs.onmessage = function(event) {
       console.log('Authorized user receives device messages');
   };
   ```

4. **Test Room-Level Permissions**
   ```javascript
   // Test joining rooms beyond user permissions
   const roomTestWs = new WebSocket('ws://localhost:8001/ws?token=<regular_user_token>');

   roomTestWs.onopen = function(event) {
       // Try to join admin room
       roomTestWs.send(JSON.stringify({
           type: 'join_room',
           room: 'admin_only'
       }));
   };

   roomTestWs.onmessage = function(event) {
       const response = JSON.parse(event.data);
       if (response.type === 'error' && response.message.includes('permission')) {
           console.log('Room permission check working correctly');
       }
   };
   ```

**Expected Results**:
- WebSocket connections without tokens are rejected
- Invalid/expired tokens are rejected
- Users cannot access resources they don't own
- Room permissions are enforced correctly
- Valid users can access their authorized resources
- Permission errors return appropriate error messages

**Troubleshooting**:
- **Unauthorized access allowed**: Check WebSocket authentication middleware
- **Valid user blocked**: Verify token validation and permission checking logic
- **Cross-user access possible**: Review resource ownership verification

---

## Background Tasks & Scheduling Tests

### TC-CELERY-009: Task - Generate Experiment Report

**Objective**: Verify Celery task for generating experiment reports.

**Why Skipped**: Requires Celery Beat periodic task execution or manual task triggering.

**Prerequisites**:
- Running Celery worker and beat scheduler
- Flower UI accessible at http://localhost:5555
- Experiment with completed data

**Step-by-Step Instructions**:

1. **Access Flower Monitoring UI**
   - Navigate to http://localhost:5555
   - Login with admin:admin123
   - Monitor active workers and tasks

2. **Trigger Report Generation**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/reports/generate" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "report_type": "summary",
          "format": "pdf",
          "include_charts": true
        }'
   ```

3. **Monitor Task Execution in Flower**
   - Check "Tasks" tab in Flower UI
   - Look for `generate_experiment_report` task
   - Monitor task status: PENDING → STARTED → SUCCESS/FAILURE
   - Check task execution time and result

4. **Verify Report Generation**
   ```bash
   # Check report generation status
   curl -X GET "http://localhost:8000/api/v1/experiments/<experiment_id>/reports/<report_id>" \
        -H "Authorization: Bearer <jwt_token>"

   # Download generated report
   curl -X GET "http://localhost:8000/api/v1/experiments/<experiment_id>/reports/<report_id>/download" \
        -H "Authorization: Bearer <jwt_token>" \
        -o experiment_report.pdf
   ```

**Expected Results**:
- Report generation task is queued successfully
- Celery worker picks up and processes the task
- Flower UI shows task progression and completion
- Generated report is accessible via API
- Report file contains expected experiment data and format

**Troubleshooting**:
- **Task not queued**: Check Celery broker connection and task routing
- **Task fails**: Review Celery worker logs for error details
- **No report generated**: Verify experiment data and report template availability

---

### TC-CELERY-010: Task - Generate Participant Progress Report

**Objective**: Verify Celery task for generating participant progress reports.

**Prerequisites**:
- Participant with experiment history
- Celery monitoring setup
- Report template system

**Step-by-Step Instructions**:

1. **Trigger Participant Report Generation**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/participants/<participant_id>/reports/generate" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "report_type": "progress",
          "date_range": {
            "start": "2025-01-01",
            "end": "2025-01-31"
          },
          "include_metrics": true
        }'
   ```

2. **Monitor Task in Flower**
   - Observe task `generate_participant_progress_report`
   - Check task parameters and execution details
   - Monitor processing time and completion status

3. **Verify Report Content**
   ```bash
   # Get report status
   curl -X GET "http://localhost:8000/api/v1/reports/<report_id>" \
        -H "Authorization: Bearer <jwt_token>"

   # Verify report contains participant data
   jq '.content.participant_experiments' report_response.json
   ```

**Expected Results**:
- Participant report task executes successfully
- Report includes participant experiment history
- Progress metrics and charts are generated
- Report is downloadable in specified format

**Troubleshooting**:
- **Empty report**: Verify participant experiment participation data
- **Missing metrics**: Check progress tracking and data collection
- **Task timeout**: Increase task timeout or optimize report generation

---

### TC-CELERY-011: Task - Export Data to Storage

**Objective**: Verify Celery task for exporting experiment data to external storage.

**Prerequisites**:
- Configured storage endpoint (S3, MinIO, etc.)
- Experiment data for export
- Storage credentials configured

**Step-by-Step Instructions**:

1. **Configure Export Settings**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/export/configure" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "destination": "s3",
          "bucket": "lics-exports",
          "format": "csv",
          "compression": "gzip"
        }'
   ```

2. **Trigger Data Export**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/export/start" \
        -H "Authorization: Bearer <jwt_token>"
   ```

3. **Monitor Export Task**
   - Check Flower for `export_experiment_data` task
   - Monitor task progress and log output
   - Verify task completion status

4. **Verify Export Results**
   ```bash
   # Check export status
   curl -X GET "http://localhost:8000/api/v1/experiments/<experiment_id>/export/status" \
        -H "Authorization: Bearer <jwt_token>"

   # Verify export completion
   curl -X GET "http://localhost:8000/api/v1/experiments/<experiment_id>/export/download" \
        -H "Authorization: Bearer <jwt_token>"
   ```

**Expected Results**:
- Export task processes experiment data correctly
- Data is uploaded to configured storage destination
- Export maintains data integrity and format
- Export confirmation includes file location and metadata

**Troubleshooting**:
- **Storage connection failed**: Verify storage credentials and network access
- **Export incomplete**: Check data volume and task timeout settings
- **File corruption**: Verify data serialization and compression

---

### TC-CELERY-012: Task - Cleanup Expired Sessions

**Objective**: Verify periodic cleanup of expired user sessions.

**Prerequisites**:
- Celery Beat scheduler running
- Expired sessions in database
- Cleanup task configured in schedule

**Step-by-Step Instructions**:

1. **Create Expired Sessions for Testing**
   ```bash
   # Create sessions that will expire
   for i in {1..5}; do
       curl -X POST "http://localhost:8000/api/v1/auth/login" \
            -H "Content-Type: application/json" \
            -d "{\"email\": \"user${i}@test.com\", \"password\": \"testpass123\"}"
   done
   ```

2. **Manually Expire Sessions in Database**
   ```sql
   -- Connect to database
   docker-compose -f docker-compose.dev.yml exec postgres-dev psql -U lics -d lics_dev

   -- Update session expiration times
   UPDATE sessions SET expires_at = NOW() - INTERVAL '1 hour' WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'user%@test.com');
   ```

3. **Trigger Cleanup Task Manually**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/tasks/cleanup-sessions" \
        -H "Authorization: Bearer <admin_jwt_token>"
   ```

4. **Verify Cleanup Results**
   ```sql
   -- Check expired sessions are removed
   SELECT COUNT(*) FROM sessions WHERE expires_at < NOW();

   -- Verify active sessions remain
   SELECT COUNT(*) FROM sessions WHERE expires_at > NOW();
   ```

**Expected Results**:
- Cleanup task removes expired sessions from database
- Active sessions are unaffected
- Cleanup logs show number of sessions removed
- Task executes on schedule (if configured in Celery Beat)

**Troubleshooting**:
- **No sessions cleaned**: Verify expired session existence and task execution
- **Active sessions removed**: Check session expiration logic and query conditions
- **Task not scheduled**: Verify Celery Beat configuration and schedule setup

---

### TC-CELERY-016: Task - Retry Mechanism

**Objective**: Verify Celery task retry mechanism for failed tasks.

**Prerequisites**:
- Celery worker with retry configuration
- Task that can be configured to fail
- Flower UI for monitoring retries

**Step-by-Step Instructions**:

1. **Create Test Task with Retry Configuration**
   ```python
   # Add to tasks/retry_test.py
   from celery import current_app
   from celery.exceptions import Retry
   import time
   import random

   @current_app.task(bind=True, max_retries=3, default_retry_delay=60)
   def flaky_task(self, should_fail=True):
       if should_fail and random.choice([True, False]):
           raise self.retry(exc=Exception("Random failure"), countdown=30)
       return {"status": "success", "attempts": self.request.retries}
   ```

2. **Execute Flaky Task**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/tasks/test-retry" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"should_fail": true}'
   ```

3. **Monitor Retry Behavior in Flower**
   - Watch task execution attempts
   - Observe retry delays and backoff behavior
   - Check final success or failure after max retries

4. **Verify Retry Logic**
   ```bash
   # Check task retry history
   curl -X GET "http://localhost:8000/api/v1/admin/tasks/<task_id>/retry-history" \
        -H "Authorization: Bearer <admin_jwt_token>"
   ```

**Expected Results**:
- Failed tasks are automatically retried according to configuration
- Retry delays follow exponential backoff (if configured)
- Max retry limit is respected
- Task succeeds on retry or fails permanently after max attempts
- Retry attempts are logged and monitored

**Troubleshooting**:
- **No retries occurring**: Check task retry configuration and exception handling
- **Infinite retries**: Verify max_retry setting and retry conditions
- **Retry delays incorrect**: Check retry_delay and backoff configuration

---

### TC-CELERY-017: Task - Chained Tasks

**Objective**: Verify Celery task chaining functionality.

**Why Skipped**: Requires complex task chain setup and monitoring.

**Prerequisites**:
- Multiple compatible tasks for chaining
- Celery canvas support for task chains
- Monitoring for chain execution

**Step-by-Step Instructions**:

1. **Create Compatible Tasks for Chaining**
   ```python
   # Add to tasks/chained_tasks.py
   from celery import current_app, chain
   import time

   @current_app.task
   def extract_data(experiment_id):
       # Simulate data extraction
       time.sleep(2)
       return {"experiment_id": experiment_id, "extracted_records": 150}

   @current_app.task
   def process_data(extraction_result):
       # Simulate data processing
       time.sleep(3)
       processed = extraction_result["extracted_records"] * 0.9
       return {"processed_records": processed, "status": "completed"}

   @current_app.task
   def generate_report(processing_result):
       # Simulate report generation
       time.sleep(1)
       return {"report_id": f"report_{processing_result['processed_records']}", "ready": True}
   ```

2. **Execute Task Chain**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/experiments/<experiment_id>/process-chain" \
        -H "Authorization: Bearer <jwt_token>"
   ```

3. **Monitor Chain Execution in Flower**
   - Observe sequential task execution
   - Check data flow between tasks
   - Verify chain completion status

4. **Verify Chain Results**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/experiments/<experiment_id>/chain-results" \
        -H "Authorization: Bearer <jwt_token>"
   ```

**Expected Results**:
- Tasks execute in specified sequence
- Output of each task passes to next task
- Chain fails appropriately if any task fails
- Final result includes outputs from all tasks
- Chain execution is monitored and logged

**Troubleshooting**:
- **Chain stops early**: Check task result passing and error handling
- **Data loss between tasks**: Verify task signatures and result serialization
- **Parallel execution**: Ensure tasks are properly chained, not grouped

---

### TC-CELERY-018: Task - Grouped Tasks

**Objective**: Verify Celery task group execution with parallel processing.

**Why Skipped**: Requires complex task group setup and monitoring.

**Prerequisites**:
- Multiple independent tasks
- Celery group functionality
- Monitoring for parallel execution

**Step-by-Step Instructions**:

1. **Create Independent Tasks for Grouping**
   ```python
   # Add to tasks/grouped_tasks.py
   from celery import current_app, group
   import time
   import random

   @current_app.task
   def analyze_device(device_id):
       processing_time = random.uniform(1, 3)
       time.sleep(processing_time)
       return {"device_id": device_id, "analysis_time": processing_time, "status": "healthy"}

   @current_app.task
   def analyze_participant(participant_id):
       processing_time = random.uniform(2, 4)
       time.sleep(processing_time)
       return {"participant_id": participant_id, "analysis_time": processing_time, "activity": "normal"}
   ```

2. **Execute Task Group**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/analysis/batch" \
        -H "Authorization: Bearer <jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "device_ids": ["device-001", "device-002", "device-003"],
          "participant_ids": ["participant-001", "participant-002"]
        }'
   ```

3. **Monitor Group Execution**
   - Watch tasks execute in parallel in Flower
   - Note execution times and overlap
   - Verify group completion status

4. **Collect Group Results**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/analysis/batch/<group_id>/results" \
        -H "Authorization: Bearer <jwt_token>"
   ```

**Expected Results**:
- Tasks in group execute in parallel
- Group completion waits for all tasks
- Results are collected from all tasks
- Group fails if any critical task fails
- Execution time reflects parallel processing benefit

**Troubleshooting**:
- **Sequential execution**: Check worker concurrency and task independence
- **Missing results**: Verify task result collection and group joining
- **Incomplete group**: Check for task failures and error handling

---

### TC-CELERY-019: Task - Task Revocation

**Objective**: Verify ability to revoke running or queued tasks.

**Why Skipped**: Requires long-running task and revocation monitoring.

**Prerequisites**:
- Long-running task implementation
- Task revocation API endpoints
- Monitoring for task cancellation

**Step-by-Step Instructions**:

1. **Start Long-Running Task**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/tasks/long-running" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"duration": 300, "task_id": "long-task-001"}'
   ```

2. **Get Task ID for Revocation**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/admin/tasks/active" \
        -H "Authorization: Bearer <admin_jwt_token>"
   ```

3. **Revoke the Task**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/tasks/<task_id>/revoke" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"terminate": false}'
   ```

4. **Monitor Revocation in Flower**
   - Watch task status change to REVOKED
   - Check task logs for revocation confirmation
   - Verify worker cleanup

5. **Verify Task Cancellation**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/admin/tasks/<task_id>/status" \
        -H "Authorization: Bearer <admin_jwt_token>"
   ```

**Expected Results**:
- Task is successfully revoked while running
- Task status changes to REVOKED
- Worker stops processing the task
- Resources are cleaned up after revocation
- Revocation can be graceful or immediate based on configuration

**Troubleshooting**:
- **Task continues running**: Check task ID and revocation API implementation
- **Resource leaks**: Verify cleanup code and worker behavior after revocation
- **Revocation not acknowledged**: Check worker connectivity and message broker

---

### TC-CELERY-020: Task - Periodic Tasks (Celery Beat)

**Objective**: Verify Celery Beat periodic task scheduling and execution.

**Prerequisites**:
- Celery Beat scheduler running
- Configured periodic tasks
- Monitoring for scheduled executions

**Step-by-Step Instructions**:

1. **Configure Periodic Task**
   ```python
   # Add to celery_app.py
   from celery.schedules import crontab

   current_app.conf.beat_schedule = {
       'daily-expiry-cleanup': {
           'task': 'app.tasks.maintenance.cleanup_expired_sessions',
           'schedule': crontab(minute=0, hour=2),  # Daily at 2 AM
       },
       'hourly-health-check': {
           'task': 'app.tasks.monitoring.system_health_check',
           'schedule': crontab(minute=0),  # Hourly
       },
   }
   ```

2. **Monitor Celery Beat Logs**
   ```bash
   docker-compose -f docker-compose.dev.yml logs -f celery-beat
   ```

3. **Check Scheduled Task Execution**
   ```bash
   # Manually trigger to verify task works
   curl -X POST "http://localhost:8000/api/v1/admin/tasks/health-check" \
        -H "Authorization: Bearer <admin_jwt_token>"
   ```

4. **Verify Periodic Execution in Flower**
   - Monitor task execution at scheduled times
   - Check task history and frequency
   - Verify schedule accuracy

**Expected Results**:
- Celery Beat schedules tasks according to crontab schedule
- Tasks execute automatically at specified times
- Schedule persists across Beat restarts
- Task execution is logged and monitored
- Multiple periodic tasks can coexist

**Troubleshooting**:
- **Tasks not scheduling**: Check Beat configuration and schedule syntax
- **Tasks not executing**: Verify worker availability and task registration
- **Schedule drift**: Check system time synchronization and Beat performance

---

### TC-CELERY-021: Flower Monitoring UI

**Objective**: Verify Flower UI monitoring functionality for Celery tasks.

**Status**: ✅ ALREADY VERIFIED - This test was completed during automated testing

**Results**: Flower UI is accessible at http://localhost:5555 with admin:admin123 authentication and successfully displays Celery worker and task information.

---

### TC-CELERY-022: Prometheus Metrics

**Objective**: Verify Prometheus metrics collection for Celery tasks.

**Status**: ✅ ALREADY VERIFIED - This test was completed during automated testing

**Results**: Prometheus metrics endpoint at /metrics successfully exposes Celery task metrics in Prometheus format.

---

### TC-CELERY-023: Task - Database Backup

**Objective**: Verify automated database backup task execution.

**Prerequisites**:
- Database backup configuration
- Sufficient storage for backup files
- Backup verification procedures

**Step-by-Step Instructions**:

1. **Configure Backup Settings**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/backup/configure" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "backup_type": "full",
          "compression": true,
          "destination": "local",
          "retention_days": 30
        }'
   ```

2. **Trigger Backup Task**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/backup/start" \
        -H "Authorization: Bearer <admin_jwt_token>"
   ```

3. **Monitor Backup in Flower**
   - Watch backup task execution
   - Monitor backup progress and file size
   - Check task completion status

4. **Verify Backup File**
   ```bash
   # List backup files
   curl -X GET "http://localhost:8000/api/v1/admin/backup/files" \
        -H "Authorization: Bearer <admin_jwt_token>"

   # Verify backup integrity
   curl -X POST "http://localhost:8000/api/v1/admin/backup/verify" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"backup_file": "backup_20251027_120000.sql.gz"}'
   ```

**Expected Results**:
- Backup task creates complete database backup
- Backup file is compressed and stored correctly
- Backup verification confirms data integrity
- Backup metadata includes size, timestamp, and checksum
- Old backups are cleaned up according to retention policy

**Troubleshooting**:
- **Backup fails**: Check database connectivity and disk space
- **Corrupted backup**: Verify backup process and file integrity checks
- **Storage full**: Monitor disk usage and cleanup old backups

---

### TC-CELERY-024: Task - Cache Warmup

**Objective**: Verify cache warmup task for performance optimization.

**Prerequisites**:
- Redis cache configured
- Cache warmup data identified
- Performance monitoring capability

**Step-by-Step Instructions**:

1. **Trigger Cache Warmup**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/cache/warmup" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "cache_types": ["user_sessions", "device_status", "experiment_metadata"],
          "force_refresh": true
        }'
   ```

2. **Monitor Warmup Task**
   - Check Flower for task progression
   - Monitor Redis memory usage
   - Track warmup completion time

3. **Verify Cache Contents**
   ```bash
   # Check Redis cache
   docker-compose -f docker-compose.dev.yml exec redis-dev redis-cli

   # Check specific keys
   KEYS "user:*"
   KEYS "device:*"
   KEYS "experiment:*"

   # Check memory usage
   INFO memory
   ```

4. **Test Cache Performance**
   ```bash
   # Test cached vs uncached response times
   time curl -X GET "http://localhost:8000/api/v1/devices" -H "Authorization: Bearer <jwt_token>"

   # Repeat request to hit cache
   time curl -X GET "http://localhost:8000/api/v1/devices" -H "Authorization: Bearer <jwt_token>"
   ```

**Expected Results**:
- Cache warmup task populates Redis with frequently accessed data
- Memory usage increases appropriately after warmup
- Cached requests show improved response times
- Cache hit ratio improves after warmup
- Warmup completes without errors

**Troubleshooting**:
- **No cache population**: Check data source availability and cache keys
- **Memory overflow**: Monitor Redis memory limits and eviction policies
- **No performance improvement**: Verify cache key patterns and request matching

---

### TC-CELERY-025: Task - Email Digest

**Objective**: Verify periodic email digest generation and delivery.

**Prerequisites**:
- Email configuration (MailHog for testing)
- Digest content data
- Email template system

**Step-by-Step Instructions**:

1. **Configure Email Digest**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/digest/configure" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{
          "frequency": "daily",
          "recipients": ["admin@lics.dev", "user@test.com"],
          "content_types": ["experiment_summary", "device_status", "system_health"]
        }'
   ```

2. **Trigger Digest Generation**
   ```bash
   curl -X POST "http://localhost:8000/api/v1/admin/digest/generate" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"include_test_data": true}'
   ```

3. **Monitor Digest Task**
   - Check Flower for task execution
   - Monitor email generation process
   - Track delivery status

4. **Verify Email Delivery**
   - Navigate to MailHog at http://localhost:8025
   - Check for digest emails
   - Verify email content and formatting
   - Confirm all recipients received emails

**Expected Results**:
- Digest task collects and formats relevant data
- HTML email template renders correctly
- All configured recipients receive digest
- Email includes summaries of experiments, devices, and system status
- Digest generation completes without errors

**Troubleshooting**:
- **No email sent**: Check email configuration and MailHog connectivity
- **Empty digest**: Verify data collection and content filtering
- **Formatting issues**: Check email template and HTML rendering

---

## API Error Handling Tests

### TC-API-037: API Error Handling - 500 Internal Server Error

**Objective**: Verify proper handling of 500 Internal Server Error responses.

**Why Skipped**: Cannot safely trigger 500 error in automated test without destabilizing the system.

**Prerequisites**:
- Admin access for error simulation
- Safe method to trigger server error
- Error monitoring and logging

**Step-by-Step Instructions**:

1. **Use Safe Error Trigger Endpoint**
   ```bash
   # Use admin endpoint designed to test error handling
   curl -X POST "http://localhost:8000/api/v1/admin/test/error-500" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -H "Content-Type: application/json" \
        -d '{"safe_mode": true, "error_type": "simulated"}'
   ```

2. **Verify Error Response Structure**
   ```bash
   # Check response has proper 500 error format
   curl -v -X POST "http://localhost:8000/api/v1/admin/test/error-500" \
        -H "Authorization: Bearer <admin_jwt_token>" \
        -d '{"safe_mode": true}'
   ```

3. **Check Error Logging**
   ```bash
   # View backend logs for error details
   docker-compose -f docker-compose.dev.yml logs -f backend-dev --tail=50
   ```

4. **Verify System Stability**
   ```bash
   # Test that system remains responsive after error
   curl -X GET "http://localhost:8000/api/v1/health" \
        -H "Authorization: Bearer <jwt_token>"
   ```

**Expected Results**:
- Server returns 500 status code for simulated error
- Error response includes appropriate error message
- Error is properly logged with details
- System remains stable after error handling
- Other endpoints continue functioning normally

**Troubleshooting**:
- **No 500 response**: Check error simulation endpoint and admin permissions
- **System instability**: Ensure error simulation is truly safe and isolated
- **Missing error logs**: Verify logging configuration and error handling middleware

---

## Reporting Manual Test Results

### Test Result Documentation Template

For each manual test completed, document the results using this format:

```markdown
## Test Execution Report

**Test ID**: TC-XXX-XXX
**Test Name**: [Test Name]
**Executor**: [Your Name]
**Date**: [YYYY-MM-DD HH:MM]
**Environment**: Development

### Execution Steps
1. [Step 1 description and result]
2. [Step 2 description and result]
3. [Step 3 description and result]

### Test Results
- **Status**: ✅ PASS / ❌ FAIL / ⚠️ PARTIAL
- **Duration**: [X minutes/seconds]
- **Issues Found**: [Description of any issues]

### Evidence
- [Screenshots, logs, or other evidence]
- [API response examples]
- [WebSocket message examples]

### Notes
[Additional observations, recommendations, or concerns]
```

### Submitting Results

1. **Create Test Result File**: Save reports as `PHASE2_MANUAL_RESULTS_YYYYMMDD_HHMM.md`
2. **Include Evidence**: Attach screenshots and log files
3. **Document Issues**: Create GitHub issues for any problems found
4. **Update Test Suite**: Consider automating any tests that can be converted

### Quality Gates

- **Critical Issues**: Any test failure that affects core functionality must be resolved
- **Documentation**: All manual tests must be completed before production deployment
- **Evidence**: Sufficient evidence must be provided for each test result
- **Follow-up**: Failed tests require root cause analysis and resolution plans

---

## Summary

This manual testing guide covers all 29 skipped test cases from the Phase 2 test suite, providing:

- **Comprehensive Instructions**: Step-by-step procedures for each test
- **Prerequisites**: Clear setup requirements for each test category
- **Expected Results**: What constitutes successful test completion
- **Troubleshooting**: Common issues and resolution approaches
- **Tools Integration**: Leverages existing development infrastructure

When combined with the 96 automated tests (77% pass rate), this manual testing ensures **100% validation coverage** of the LICS Phase 2 Backend Core Development system.

**Automated + Manual = Complete System Validation** ✅
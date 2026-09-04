# REST API Reference: Prompt Compilation & Optimization

**Base Path:** `/v1/tenants/{tenantId}/prompts`  
**Authentication:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>` or Tenant Bearer Token (for read-only queries)  
**Milestone:** 92 (Phase L)  

---

## Endpoints

### 1. Compile Prompt Program

Triggers teleprompter optimization for the specified tenant.

- **Method:** `POST`
- **Path:** `/v1/tenants/{tenantId}/prompts/compile`
- **Headers:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
- **Request Body:**
  ```json
  {
    "name": "support_cot_v1",
    "dataset_id": null,
    "optimizer": "BootstrapFewShot",
    "max_demos": 3,
    "metric_target": "composite",
    "train_data": [ ... ],
    "val_data": [ ... ]
  }
  ```
- **Response (`200 OK`):**
  ```json
  {
    "program_id": "prog_719a896ff6f44ec8",
    "tenant_id": "848da0c4-a690-4101-bca6-5a40989f6b4e",
    "name": "support_cot_v1",
    "signature_name": "RAGAnswerSignature",
    "optimizer": "BootstrapFewShot",
    "dataset_id": null,
    "baseline_score": 0.684,
    "compiled_score": 0.892,
    "improvement_pct": 30.41,
    "metric_name": "composite",
    "compiled_instruction": "You are Retriever's optimized cognitive agent...",
    "few_shot_demos": [
      {
        "question": "What is the maximum single document upload limit?",
        "context": "Retriever limits single document uploads to 50MB...",
        "thought": "Extract maximum file size constraint directly.",
        "answer": "The maximum single document upload limit is 50MB.",
        "score": 0.98
      }
    ],
    "is_active": false,
    "created_at": "2026-09-04T16:50:00.000Z"
  }
  ```

---

### 2. List Compiled Programs

Returns all saved compiled prompt programs for the tenant.

- **Method:** `GET`
- **Path:** `/v1/tenants/{tenantId}/prompts/compiled`
- **Response (`200 OK`):** Array of `CompiledPromptProgram` objects.

---

### 3. Get Active Compiled Program

Returns the currently hot-activated prompt program, or `null` if the tenant is using standard handcrafted templates.

- **Method:** `GET`
- **Path:** `/v1/tenants/{tenantId}/prompts/compiled/active`
- **Response (`200 OK`):** `CompiledPromptProgram` or `null`.

---

### 4. Activate Compiled Program

Atomically activates the compiled program in production. Deactivates any previously active program.

- **Method:** `POST`
- **Path:** `/v1/tenants/{tenantId}/prompts/compiled/{programId}/activate`
- **Response (`200 OK`):** Updated `CompiledPromptProgram` with `is_active: true`.

---

### 5. Deactivate Compiled Program

Deactivates the compiled program, reverting chat inference to standard handcrafted templates.

- **Method:** `POST`
- **Path:** `/v1/tenants/{tenantId}/prompts/compiled/{programId}/deactivate`
- **Response (`200 OK`):** Updated `CompiledPromptProgram` with `is_active: false`.

---

### 6. Delete Compiled Program

Permanently deletes the compiled prompt program.

- **Method:** `DELETE`
- **Path:** `/v1/tenants/{tenantId}/prompts/compiled/{programId}`
- **Response (`200 OK`):**
  ```json
  {
    "success": true,
    "program_id": "prog_719a896ff6f44ec8"
  }
  ```

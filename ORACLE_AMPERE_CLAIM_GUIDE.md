# Oracle Cloud Ampere 24GB Auto-Claim Setup Guide

> **Purpose:** Step-by-step instructions to activate the automated 24/7 GitHub Action workflow (`.github/workflows/oracle-claim-ampere.yml`) that claims an Oracle Ampere A1.Flex (4 OCPU, 24 GB RAM) instance for $0/mo forever.

---

## Step 1: Collect OCI OCIDs & API Key (Oracle Cloud Console)

Log in to [cloud.oracle.com](https://cloud.oracle.com):

1. **User OCID & API Key:**
   - Click **Profile Icon** (Top Right) → **User Settings**.
   - Click **API Keys** (Left Menu) → Click **Add API Key**.
   - Select **Generate API Key Pair** → Click **Download Private Key (`.pem`)** → Click **Add**.
   - Copy the **User OCID** (`ocid1.user...`) and **Fingerprint** (`aa:bb:cc...`) displayed on screen.
   - Open the downloaded `.pem` file in a text editor and copy its entire content (including `-----BEGIN RSA PRIVATE KEY-----`).

2. **Tenancy OCID:**
   - Click **Profile Icon** (Top Right) → **Tenancy: <your_tenancy_name>** → Copy **Tenancy OCID** (`ocid1.tenancy...`).

3. **Compartment & Subnet OCID:**
   - Navigation Menu (Top Left ☰) → **Identity & Security** → **Compartments** → Copy **Compartment OCID**.
   - Navigation Menu → **Networking** → **Virtual Cloud Networks** → Select VCN → **Subnets** → Copy **Subnet OCID**.
   - Note down your exact **Availability Domain** name (e.g., `US-ASHBURN-AD-1` or `IN-MUMBAI-1-AD-1`).

---

## Step 2: Add Secrets to GitHub Repository

1. Go to GitHub: `github.com/prat3010/retriever`
2. Go to **Settings** → **Secrets and variables** → **Actions** → Click **New repository secret**.
3. Add the following 10 secrets:

| Secret Name | Value |
| :--- | :--- |
| `OCI_USER_OCID` | User OCID (`ocid1.user.oc1...`) |
| `OCI_TENANCY_OCID` | Tenancy OCID (`ocid1.tenancy.oc1...`) |
| `OCI_FINGERPRINT` | API Key Fingerprint (`aa:bb:cc...`) |
| `OCI_KEY_CONTENT` | Complete text from the downloaded `.pem` file |
| `OCI_REGION` | Your Oracle Region (e.g. `us-ashburn-1` or `ap-mumbai-1`) |
| `OCI_COMPARTMENT_OCID` | Compartment OCID |
| `OCI_SUBNET_OCID` | Subnet OCID |
| `OCI_AVAILABILITY_DOMAIN` | Availability Domain Name (e.g., `US-ASHBURN-AD-1`) |
| `OCI_IMAGE_ID` | Canonical Ubuntu 24.04 ARM Image OCID |
| `SSH_PUBLIC_KEY` | Public SSH Key (`cat ~/.ssh/oracle_rsa.pub`) |

---

## Step 3: Run / Monitor Workflow

1. Go to GitHub Repository → **Actions** tab.
2. Select **Oracle Cloud Ampere A1.Flex Auto-Claim** workflow.
3. Click **Run workflow** (or let the 15-minute cron schedule run automatically).
4. Once capacity opens up, the workflow will automatically provision the 24 GB ARM instance and log completion!

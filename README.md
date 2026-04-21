# Tucker and Dale's Home Services

## Table of Contents

(ctrl+click links to navigate)

> **Note:**
> Some internal links in this README may not jump to the correct section when viewed from the repository landing page.
> This is due to a known GitHub rendering limitation affecting in-page anchor navigation.
> If a link does not scroll correctly, open the README file directly or use your browser’s search (Ctrl+F).
> Or, go directly to https://github.com/Pacman0126/tucker-and-dales-home-services/blob/main/README.md which is
> easier to navigate without launching new browser tabs

GitHub Community: https://github.com/orgs/community/discussions/60984?utm_source=chatgpt.com


- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [User Stories & Agile Mapping](#user-stories--agile-mapping)

- [Application Architecture](#application-architecture)
- [Entity Relationship Diagrams](#entity-relationship-diagrams)

  - [Scheduling App](#scheduling-app-erd)
  - [Billing App](#billing-app-erd)
  - [Customers App](#customers-app-erd)
  - [Core App (ERD)](#core-app-erd)
  - [Project-Wide ERD](#project-wide-erd)

  - [Apps Overview](#apps-overview)
  - [Scheduling App Overview](#scheduling-app-overview)
  - [Billing App Overview](#billing-app-overview)
  - [Customers App Overview](#customers-app-overview)
  - [Core App Overview](#core-app-overview)

- [CRUD & Booking Lifecycle](#crud--booking-lifecycle)
- [Booking Lifecycle & Defensive Programming](#booking-lifecycle--defensive-programming)

- [Functional Testing](#functional-testing)
  - [VT-10A Authentication](#vt-10a--functional-testing-authentication--account-workflow)
  - [VT-10B Booking & Checkout](#vt-10b--functional-testing-booking--checkout-workflow)

- [Testing & Validation](#testing--validation)
  - [Manual Testing](#manual-testing)
  - [Validation Summary](#validation-summary)
  - [VT-05 HTML Validation](#vt-05-html-validation)

  - [VT-06 CSS Validation](#vt-06-css-validation)
  - [VT-07 JavaScript Validation](#vt-07-javascript-validation)
  - [VT-08 Python Validation](#vt-08-python-validation)

- [User Stories](#user-stories)
- [User Story Results](#user-story-results)

- [UX & Design](#ux--design)
- [Authentication & Access Control](#authentication--access-control)

- [Deployment](#deployment)
  - [Setup Database](#2-setup-database)
  - [Website Domain and Email Host Deployment](#website-domain-and-email-host-deployment)
  - [Setup Website Domain](#setup-website-domain)
  - [Setup Email Host](#setup-email-host-brevocom)
  - [Deployment (Heroku)](#deployment-heroku)
  - [Custom Domain & Deployment Configuration](#custom-domain--deployment-configuration)

- [SEO & Discoverability](#seo--discoverability)
- [Marketing & Business Model](#marketing--business-model)
- [E-Commerce Business Model](#e-commerce-business-model)


## Project Overview

A family owned home services company approached us to help them modernize their business
for future expansion. They have an existing customer base and 15 employees in the Greater
Dallas Area, Texas. This application stores all customers, employees, and service addresses in a structured database. A user can browse available employees and services that are within 30 minutes
drive from their current active jobsite location or the employee's home. All employees within
30 minutes of the customer are rendered to Google Maps with color coded points and driving routes.

This ensures only geographically feasible service options are presented, improving scheduling reliability and reducing failed bookings.

The user can search by 2 hour time slots or search for available services on a specific date. The
results can be added to a shopping cart by dragging and dropping. Upon successful registration and
checkout, the user can pay for services and receive an email receipt. First time users will
automatically be signed up for an email newsletter. PDF receipts can also be downloaded. Each booking
of services will receive a card for each address that they may have as a landlord for instance.
This design supports landlord and multi-property use cases by consolidating all activity per address into a single financial record.
These are stored in the customer's payment history, where cancellation for individual service
line items is possible to receive a refund to the credit card.

Owner/Manager has full admin rights to add/remove employees, find employees work schedules, access
customers and payment history.

This application stores customers, employees, and service addresses in a database. Users can:

* Browse available employees and services within a 30-minute drive radius
* View employees plotted on Google Maps with routes
* Search by date or time slot
* Add services via drag-and-drop into a cart
* Checkout securely using Stripe
* Receive email and PDF receipts
* Track bookings per address (landlord use-case)

Each booking generates a **per-address invoice card**, supporting:

* ongoing service tracking
* cancellations and refunds
* tax reporting use cases

Admins can:

* manage employees
* view schedules
* access customer and payment history

### Test Data & Usage Instructions

This project is pre-populated with realistic **test data**, including customers, employees, service addresses, and bookings. All data is synthetic and intended to simulate real-world usage.

To fully test the scheduling and availability features, the assessor should:

- Use a **real, valid address** from the **Greater Dallas, Texas area** (e.g., Dallas, Plano, Frisco, Irving). Note: This project used Google Maps during development.
- The system uses **geographic proximity and travel-time logic**, so only valid addresses within this region will return meaningful results
- Random or non-regional addresses may result in no available services being displayed
- A staff member has already been added for testing purposes. demo: username=Dale/password=$Hannah71 at 9690 Forest Ln, Dallas, TX 75243, United States,
  This can be used for testing by selecting a random customer address near this on Goodle Maps or similar.
- For a full staff workflow, add via superuser in admin using a temporary email address where verification starts for a new staff member

This ensures that availability filtering, employee assignment, and booking workflows behave as designed.

[Back to Table of Contents](#table-of-contents)
---

## Key Features

### Booking & Scheduling

* Search by date OR time slot
* Preloaded realistic test dataset (customers, employees, bookings) with location-based filtering using Greater Dallas service coverage
* Travel-aware availability filtering
(Availability is validated using employee scheduling constraints and travel-time feasibility checks)
* Drag-and-drop booking
* Real-time availability updates


### Payments & Billing

* Stripe checkout integration
* Stripe webhooks are handled idempotently to prevent duplicate transactions during retry events.
* Payment history per address (supports long-term financial tracking and tax reporting)
* Refund & cancellation workflow
* Invoice generation (PDF)

### User System

* Django Allauth authentication
* Profile-based booking history
* Email notifications (Brevo)

### Admin System

* Full CRUD for employees, bookings, services
* Read-only staff dashboards
* Full payment visibility

[Back to Table of Contents](#table-of-contents)
---

## User Stories & Agile Mapping

This project was developed using an Agile approach, where features were defined through user stories and implemented incrementally.

User roles include:
- Customer (booking and checkout)
- Staff (schedule visibility)
- Admin (system management)

Each implemented feature maps directly to a user story, ensuring traceability between requirements and delivered functionality.

[Back to Table of Contents](#table-of-contents)

## Application Architecture

The application follows a modular Django architecture, separating concerns across multiple apps:

- **core** → user accounts and address management
- **customers** → customer profiles and reusable CRUD patterns
- **scheduling** → booking logic, availability, and employee assignment
- **billing** → cart, checkout, and payment processing

Each app is responsible for a distinct domain, improving maintainability, scalability, and testability.

The system follows a standard request lifecycle:

request → validation → availability checks → persistence → payment → analytics

This structure ensures clear data flow, separation of concerns, and reliable transaction handling across the platform.

[Back to Table of Contents](#table-of-contents)

## Entity Relationship Diagrams

### Scheduling App (ERD)

I have also used [Mermaid](https://mermaid.live) with ChatGPT to generate an interactive ERD of the project.

**Scope:** Booking lifecycle, employees, time slots, and routing

**ERD Note:** PaymentHistory participates in booking flow in three ways:

  - **FK:** PaymentHistory.booking
  - **M2M:** linked_bookings
  - **FK:** Booking.primary_payment_record


```mermaid
 erDiagram
    %% ============================================
    %% SCHEDULING CORE
    %% ============================================
    USER ||--o{ BOOKING : "creates → service request"

    SERVICECATEGORY ||--o{ EMPLOYEE : "assigned skill/service"
    SERVICECATEGORY ||--o{ BOOKING : "booked under"
    SERVICECATEGORY ||--o{ CARTITEM : "references"

    TIMESLOT ||--o{ BOOKING : "scheduled in"
    TIMESLOT ||--o{ CARTITEM : "selected slot"

    EMPLOYEE ||--o{ BOOKING : "assigned to"
    EMPLOYEE ||--o{ CARTITEM : "selected employee"
    EMPLOYEE ||--o{ JOBASSIGNMENT : "has route assignments"

    BOOKING ||--o{ JOBASSIGNMENT : "creates job assignment"
    BOOKING ||--o{ PAYMENTHISTORY : "payment records"
    BOOKING ||--o| PAYMENTHISTORY : "primary_payment_record"

    PAYMENTHISTORY ||--o{ PAYMENTHISTORY : "parent → adjustments"
    PAYMENTHISTORY ||--o{ BOOKING : "linked_bookings (M2M)"
    PAYMENTHISTORY ||--|| USER : "belongs to"

    CART ||--o{ CARTITEM : "contains"
    CART ||--|| USER : "belongs to"
    PAYMENTHISTORY ||--|| CART : "originates from checkout"

    USER {
      int id
      string username
      string email
      string password
    }

    SERVICECATEGORY {
      int id
      string name
    }

    EMPLOYEE {
      int id
      string name
      string home_address
    }

    TIMESLOT {
      int id
      string label
    }

    BOOKING {
      int id
      date date
      string service_address
      decimal unit_price
      decimal total_amount
      string status "Booked / Cancelled / Completed"
      datetime created_at
      datetime updated_at
    }

    JOBASSIGNMENT {
      int id
      string jobsite_address
    }

    CART {
      int id
      string session_key
      string address_key
      datetime created_at
      datetime updated_at
    }

    CARTITEM {
      int id
      string service_address
      date date
      decimal unit_price
      int quantity
      decimal subtotal "computed property"
    }

    PAYMENTHISTORY {
      int id
      decimal amount
      decimal adjustments_total_amt
      string currency
      string status "Paid / Cancelled / Refunded / Adjustment"
      text service_address
      string payment_type
      string stripe_payment_id
      text notes
      datetime created_at
      json raw_data
    }

```

[View on Mermaid Live](https://mermaid.live/edit#pako:eNqlVu2O2jgUfRXLUqWtNJ3yUYaC1B8MjabsDsMI6EpTIUWe5A54SOzUdrZlB_7uA-wj9kl6nZAAHkJbNT8gsX3Ovb73-CRPNJAh0C4F9Z6zuWLxTBC8Xrwg737hKkGT_gfv_cfrwc0V6Y_G3m-QfZx4Y7Jev3oln8jlaPSXpeySGQ0UMAOafPvvf6JB_cMDIAo-p6DNjM5EDkbs34O-1-9NvavR-K7g8Ya316M7z8uImNZ8LiAkesmj6PWWy3KcYNjP5F7KJcJTEYL6AazfG08HU2-Y4RQ8gAIRgN4lPB0Mvcn1aHosjg4WEKYRhuKiiOOuPwigIYLA2J1Fcq8o5e6PxCiLYWQRwl1-PATESSRXAFWoP0eXvclkcHUz9G6mGXTBNFEyNUDyoDEIs1eJIqtKfCGAR3m_x1DEd-C3vTsL_DCYTG07LD5hKwtA0QRShfoocH0UqHjM1MrfEvg5wS5zB3IqA2UTsApm4WOqTVmCapr9ZkVcoPB8qz8u5pr8MWwMX56Ar9f5acpEC5G0mLzPOcR29miXAykM46JMrVxYzVidQga2AKn4nIushw9KxgTlHSxRELuEMu6n_J6g6g3hYfGkjcJNkxTPq2AxOMMQMx45Ywmq5IvtVDa8qfKI0_F2sTbPztPPIsuhhYzBZ2GoQGuHtDzYp0kjhmV3oIVEKpAhVjz7cai2xneYDy6HAOUeob1x46P0A3BnjDQs8lksUzx-DqdhJtXY68vcI1-TPkPDi6L8XqJpALpHIZg8OcNjIPnpDn1mnk2lSXgwVW780CNOFw5dQ3NTVf1Mo6cJNKK4FP4SVs7MlnJ_5re2VR7FHyV0vH9uu6sbamk_p0wYblbuap3eZ33O3CBOUuv5iZIJKFxLnYydg18lxC31oXLK0Z0j-oXCXHkFqbIv0FWV6m4ZdzU3hgf7ora3vTLCTn8GvpqqSpY2ktu-WSXPjhD-JVC-GHZbzWiFRKv7CUU8aimIYl98XMPKyhJCz-hc8ZB2jUrhjMag0OTwkWb1nVGzAHQYaq01ZGppN7VBTMLEJynjAoav3PmCdh9YpPEpF932k69cAvZTpm-7Qrv1er2dkdDuE_2Kz83Wea120XxbazbbjUan0zyjKxyu1c5bndqbt-1OvVWrN-rNzRn9N4tbP6_XGq3mm3a71rlotdoXjc1361E5KA)

[Back to Table of Contents](#table-of-contents)

### Billing App (ERD)

I have also used [Mermaid](https://mermaid.live) with ChatGPT to generate an interactive ERD of the project.

**Scope:** Cart, checkout, payments, and financial tracking

**Key Design:**
  - PaymentHistory = business/accounting layer
  - Payment = Stripe transaction layer

```mermaid
erDiagram
    %% =========================
    %% RELATIONSHIPS
    %% =========================

    USER ||--o{ CART : "owns"
    CART ||--o{ CARTITEM : "contains"

    CARTITEM ||--|| SERVICECATEGORY : "references"
    CARTITEM ||--|| TIMESLOT : "for time slot"
    CARTITEM ||--|| EMPLOYEE : "selected employee"

    USER ||--o{ PAYMENTHISTORY : "makes payments"
    USER ||--o{ PAYMENT : "initiates Stripe payment"

    PAYMENTHISTORY ||--o{ PAYMENTHISTORY : "has child adjustments (refunds/add-ons)"
    PAYMENTHISTORY ||--o{ BOOKING : "linked_bookings (M2M)"
    PAYMENTHISTORY ||--|| BOOKING : "primary booking"
    PAYMENTHISTORY ||--|| CART : "originates from checkout"
    PAYMENTHISTORY ||--|| USER : "belongs to payer"

    BOOKING ||--|| USER : "requested by"
    BOOKING ||--|| SERVICECATEGORY : "service type"
    BOOKING ||--|| TIMESLOT : "scheduled in"
    BOOKING ||--|| EMPLOYEE : "assigned staff"
    BOOKING ||--o| PAYMENTHISTORY : "primary_payment_record"

    PAYMENT ||--|| USER : "belongs to payer"

    %% =========================
    %% ENTITY DEFINITIONS
    %% =========================

    USER {
      int id
      string username
      string email
    }

    SERVICECATEGORY {
      int id
      string name
    }

    TIMESLOT {
      int id
      string label
    }

    EMPLOYEE {
      int id
      string name
      string home_address
    }

    BOOKING {
      int id
      date date
      string service_address
      decimal unit_price
      decimal total_amount
      string status "Booked / Cancelled / Completed"
      datetime created_at
      datetime updated_at
    }

    CART {
      int id
      string session_key
      string address_key
      datetime created_at
      datetime updated_at
    }

    CARTITEM {
      int id
      string service_address
      decimal unit_price
      int quantity
      date date
      decimal subtotal "computed property"
      datetime created_at
    }

    PAYMENTHISTORY {
      int id
      decimal amount
      decimal adjustments_total_amt
      string currency
      string status "Paid / Cancelled / Refunded / Adjustment"
      string payment_type
      text service_address
      string stripe_payment_id
      text notes
      datetime created_at
      json raw_data
    }

    PAYMENT {
      int id
      int amount
      string currency
      string stripe_payment_intent_id
      string stripe_checkout_session_id
      string status
      string description
      string receipt_url
      json metadata
      datetime created_at
      datetime updated_at
    }

    %% =========================
    %% LOGIC FLOW NOTES
    %% =========================
    %% Primary flow: CART -> PAYMENTHISTORY -> BOOKING
    %% Refunds and adjustments are child PAYMENTHISTORY entries linked by parent_id
    %% Stripe transaction storage is separated into PAYMENT
```
[View on Mermaid Live](https://mermaid.live/edit#pako:eNqlV22P2jgQ_itWpEo9aXcLy8HuIt1JlKbbqLwJuDvtaaXImwzgktjUdm7LLfz3Tpw3khLKqvmAEnuemfHjxzPmxfKED1bXAvmB0aWk4SMn-Lx5Q_6oe3KLqT3ozZ3xaPbJmczOwSU2f83sKdntLi_FC-n3pnPSJY-WeObq0UoMzOCBgTO3h8bIE1xTlhgWpmY6Nt_tCLr-2-nb_d7cvh9PHwxKwgIkcA9KAQ5Rc2dozwbjJJOFkESzEIgKhK5D2MPJYPxg2wahIABPg08g3ARiC1Dkd7jWSe9haI_mn5zZPEstpGtQZEO3IXCdp3cEZKwZZ5pRjYiZlmwDGbAIVwlRH3hFFfFWLPAJ9b9ESpv45C1SFXFfvaO-fym4-i3L6Ljf9-PxZ2d0bxwGjK_Bd5-EWDO-RFfD6-EpOHJ4CN9IFlK5JSn-NLAQjWRLxg0jCylCXBF4axHp03BDbwx_gkDEuWoRMwmy4DFLrYqQ8DUCFW_10zYLUrE9pkAF8j_mAdHbDdTAShJUuBA_CjAM4zX2JQFSpdiSo7nSdLE4hhC7YypIWXdTHbkSPCH9H-T0CuLOqhvo0pk_kA_2R2fkmALyyuLxkrwTpEcT5mdfCk8FX5II6eY0hMowhJQFydg-81bdrNOOC6e5g3zbTiMDipRVoPkOnhs0H1qJEFw8ohKUqjjN9rzGp49nxfxUPKYCLTtFc_BQIAGJsPC4KBYPqjNaaBq4NBQRlqGKT011pFAt7_FMozbfkT7FIhwEybvAWgl4kjK1JsmZwutJwFffpfqHqWjjl6b2h43gJ0wqXBkT3F3DtjKTLvtw5peTMd3iZwm9kvXYy9eIcs30tnZLM7iKnszumL4ZbqK4am2k2IDU2zNI39f0lDplpVHLUshHiybjZpKp6sWLZNylt3UymlBWFdHUtCvz2ssjFGtLPWTVzVTfdErDN13Hfx447rF5bSyWarBcYNc5QyxflOBE0mcXbehxZusojb-OnqxapsoJc13Ou2yW9Uo3OxZHDGPmK4M-KA_xGhGVGWwegBNuJIPS4kPQtFj8L56ss_rLYHzv9MnHwfgfMhrP7dkroJP0HrIIxHM3KSqXf1aPAI6kdba4CicXJ0J5-UZFJaT3rIoPnJUM7y3JvQmvEyhTebhf6DS95WlJuaJeTDlyLSRdAmEK1YuImKVYKCLzH4OtC2spmW91tYzgwgpBYuvDT8sI7dHSK8CeYsWd3KdyHR-YPWI2lP8rRJjBpIiWK6u7oIHCr2RH0v8I-Shm7IPsxxq1uu1Gyzixui_WN6vbbDWvmp12o33X6dw2OtfXF9YWja5u2s125_e72-ubVueu2dlfWP-bqI0rtGrd3bZub246zUaj095_B5d-5Rk)

[Back to Table of Contents](#table-of-contents)

### Customers App (ERD)

I have also used [Mermaid](https://mermaid.live) with ChatGPT to generate an interactive ERD of the project.

Scope: Customer profile and address data

**Design Note:**
Address data is stored in CustomerProfile and duplicated into booking/payment records as snapshots, avoiding dependency on mutable address records.

```mermaid
erDiagram
    %% =========================
    %% RELATIONSHIPS
    %% =========================

    USER ||--|| CUSTOMERPROFILE : "extends user"

    USER ||--o{ BOOKING : "creates service requests"
    USER ||--o{ PAYMENTHISTORY : "makes payments"
    USER ||--o{ CART : "owns checkout carts"

    BOOKING ||--|| SERVICECATEGORY : "service type"
    BOOKING ||--|| TIMESLOT : "scheduled in"
    BOOKING ||--|| EMPLOYEE : "assigned staff"

    %% =========================
    %% ENTITY DEFINITIONS
    %% =========================

    USER {
      int id
      string username
      string email
      string password
      bool is_active
    }

    CUSTOMERPROFILE {
      int id
      string phone
      string email
      string company
      string preferred_contact "email / phone"
      string timezone
      string billing_street_address
      string billing_city
      string billing_state
      string billing_zipcode
      string region
      string service_street_address
      string service_city
      string service_state
      string service_zipcode
      string service_region
      datetime created_at
      datetime updated_at
    }

    BOOKING {
      int id
      date date
      string service_address
      decimal unit_price
      decimal total_amount
      string status "Booked / Cancelled / Completed"
      datetime created_at
      datetime updated_at
    }

    SERVICECATEGORY {
      int id
      string name
    }

    TIMESLOT {
      int id
      string label
    }

    EMPLOYEE {
      int id
      string name
      string home_address
    }

    PAYMENTHISTORY {
      int id
      decimal amount
      decimal adjustments_total_amt
      string currency
      string status "Paid / Cancelled / Refunded / Adjustment"
      text service_address
      string payment_type
      string stripe_payment_id
      text notes
      datetime created_at
      json raw_data
    }

    CART {
      int id
      string session_key
      string address_key
      datetime created_at
      datetime updated_at
    }


```
---
     **LOGIC FLOW NOTES**

    - USER -> CUSTOMERPROFILE stores contact, billing, and service address data
    - BOOKING and PAYMENTHISTORY store service_address snapshots directly
    - CART ownership remains tied to USER/session, not CUSTOMERPROFILE
---

[View on Mermaid Live](https://mermaid.live/edit#pako:eNqlVm1v2joU_iuWpX2jLV1b3qRdibG0iy4lCNiuOlWK3OQAHomdazvraMt_30lIwmoaxLR8gMQ-z3nxc178TAMZAu1RUJ84WygW3wuCz7t35EPdU0lMnGF_5nqj6Wd3PD0Gt5X5MnUm5OXl5OTlhQy-TGferTMZT7xrd-iQHrmn8NOACDVJNah7uoeSz-Sj5_3rjm5y6UABM6AJCv_gARAF_6egjc6QNm7cv7t1RrPPLhqd3OXwmK0QnLB1DOJt0KA_meWi8lFoEiwhWMnUkICprfwWUbpUxIX4r-7AGfRnzk1pqvTQrBMoDVmwmXvrTIfe1p5GW2EaQUi4qJF3bsdD787ZnhvTmi8EimvD5vOda0dxicfizu7IJ-faHbk5qX9I6PP2naCzhvCw_NJGcbHIuRQsBmsZYsYjay3BOB6lqjQ8SBkRrn0WGP6jULApTdv5c9iLZCnFMS4EMk6YWNtoBXNQCkI_kMKgO1muZmhyVmimFsLwGJ72TT7wKMJ_Hz8BjM_CUIHWNUIBN-taPGZ-zd4TT7LKtnYVLLgU1mKRl4fdKYXecGeH33en3HvbnXL3tVshqslOjmxLO_SZ2dtKk_DV1sauw5pEyFD5T40nVvAhBDxmEUkFN36iUMLeMdKwyGexTIWxdeJ5pBqT5KOUKyzLMzJgIoAo2r5jjkWAMeyy5q8CtzvO4UrY1WKloOo9h5ERe4DIglZt6Fij1dJSxtahV0qtZl1HaMHDawaq1fB7qk3e2v2SKZumIMWaFsG6jr0x4zZ3E5inIsxf-5WFHY8GJ1hdRlVNLh84fj4LbMOKJ-CXErtQc7VC4rA7ImG-aymIYo8-yjC7aWYT7TBVGl3GkvRXYJ9LEc_vO3-Vt0dNp6F34w7I9dD7j4y8mTP9A2g-nE7-2ZsU2kiMgxStvFE2zgZhIqwuE0WwZHeIqLFsMZmglaS5Upt6ogVL9FIa1MMVBCZaV7pyKvBiAUoveYL9GecJ3jIMx-QyMnf-rOCikXFvh5Epog26UDykPaNSaNAYFCrBT5pTfE_NErDuaHZFCJlaZXm6QQxOuG9SxiVMyXSxpL05izR-bekqroTVKtZJCGqQVRrttTvnuRLae6Y_ae_8qnXabrbaF51267J51e1eNOgal5ut0_dXndb5RafbvGydNzubBn3K7TZPW52rVrfd7La6nWbz_WVn8wvsjEc8)

[Back to Table of Contents](#table-of-contents)

### Core App (ERD)

I have also used [Mermaid](https://mermaid.live) with ChatGPT to generate an interactive ERD of the project.

Scope: Shared foundational models

**Design Note:**
Address remains a reusable model, but is not directly linked to booking or payment flows in the final design.

```mermaid
erDiagram
    %% =========================
    %% RELATIONSHIPS
    %% =========================

    USER ||--o{ ADDRESS : "owns multiple addresses"
    USER ||--o| NEWSLETTERSUBSCRIPTION : "has newsletter preferences"

    %% =========================
    %% ENTITY DEFINITIONS
    %% =========================

    USER {
      int id
      string username
      string email
      string password
      bool is_active
    }

    ADDRESS {
      int id
      string label           "e.g. Home, Rental A"
      string line1
      string line2
      string city
      string state
      string postal_code
      string country         "2-letter ISO code"
    }

    NEWSLETTERSUBSCRIPTION {
      int id
      date next_send_on
      bool unsubscribed
      string token
      datetime created_at
      datetime updated_at
    }

```

[View on Mermaid Live](https://mermaid.live/edit#pako:eNqVVO9v2jAQ_VdOlqp9oQxSfkbaBwppG42RKqGqOiEhJ7mC1cSJbKeUUf73OYFAm41pWIpkn_2e717eeUOCJERiEhQjRheCxjMOelxcwLdT43DCtcaDqe1MvDv73vsf3O7Mg2e58P5-eZlsYDAauZbngQkzkqy4hDiLFEsjBBqGAqVEOSNV2DtMrEdvbE2nlus9XHtD177P8yhYllQCx5WMUCkUkAp8RoE82BGdUZ01mdrTJxhZN_bELso8s8TNbg7AuAIWliupBOMLyCQKTmOshDGmLKrEUirlKhEHBj9JImByTgPFXvcE2_LqUtF_3x5RHyM4jhnB-qIOd0mMNXCRKxrBoFT-iGIcm3-JGZVYwNS6EpKKqmqtaaKj0Tx3YJUgybgS6w_pGZf7H2p7DhQIUin8hCdO6BDqdLRP3tRcIg_nCf8kbsZl5stAMB-ryqnkBflHFsVihECgnoZzqv7YytLw09b2LBeOnVt7CDdj5xEmztTyzoDmJvQgoBx0Zx0bqzSIwEB7SmpdQC0Rho5rAU3T-gF_PKg9qVuT6lkmqa85NBIh1n8hqoGfKbh2nO_25BYoD-F-8PRD986d7U0d9-nAxpOVljDHaeO_sgC_-iyKckX3nQ6S01QuEyUhZDo5Fa1BUJ2a0PnRo2ZlQ-fQMkV_Dc-ami04vOD6WMIJTxR5SEAaLIs-_PLpycgNsfNrQURqZCFYSEwlMqyRGIWWQy9J4awZ0RnqLib52xNS8ZL7cqsxKeU_kyQuYSLJFktiPtNI6tXOE_sX9xDVVYUohrn3idlpFBzE3JA3YjYb_Xrrqtnt9HvtVrvf7tbImphGt94xWka31Wu0u0azZ7S3NfKruLVR77Y6PaNhGB39Na-6_e1vjZfCzA)

[Back to Table of Contents](#table-of-contents)

### **Project-Wide ERD**

(all data relationships across apps)

I have also used [Mermaid](https://mermaid.live) with ChatGPT to generate an interactive ERD of the project.

### 🔹 ERD Color Legend

|       Color       | App / Module | Description                                                                                                                        |
| :---------------: | :----------- | :--------------------------------------------------------------------------------------------------------------------------------- |
|    🟦 **Core**    | `core`       | Shared foundation models and reusable utilities (`User`, `Address`, `NewsletterSubscription`)                                      |
|  🟩 **Customers** | `customers`  | Customer profile, billing, and service address data (`CustomerProfile`)                                                            |
| 🟧 **Scheduling** | `scheduling` | Booking flow, employees, services, time slots, and routing (`Booking`, `Employee`, `ServiceCategory`, `TimeSlot`, `JobAssignment`) |
|   💗 **Billing**  | `billing`    | Cart, payment history, and Stripe transaction records (`Cart`, `CartItem`, `PaymentHistory`, `Payment`)                            |
                          |


💡 Tip:
User is the primary ownership anchor across the system. The colors above correspond to each app’s models as shown in the ERD.
CustomerProfile stores profile and address data, while operational models (Booking, PaymentHistory) store address snapshots for consistency in checkout, invoicing, and reporting.

```mermaid
erDiagram
    %% ============================================
    %% USERS & CORE PROFILE DATA
    %% ============================================
    USER ||--o{ ADDRESS : "owns → multiple addresses"
    USER ||--|| CUSTOMERPROFILE : "extends → customer info"
    USER ||--o| NEWSLETTERSUBSCRIPTION : "has newsletter preferences"

    ADDRESS {
      int id
      string label
      string line1
      string line2
      string city
      string state
      string postal_code
      string country
    }

    CUSTOMERPROFILE {
      int id
      string phone
      string email
      string company
      string preferred_contact
      string timezone
      string billing_street_address
      string billing_city
      string billing_state
      string billing_zipcode
      string region
      string service_street_address
      string service_city
      string service_state
      string service_zipcode
      string service_region
      datetime created_at
      datetime updated_at
    }

    NEWSLETTERSUBSCRIPTION {
      int id
      date next_send_on
      bool unsubscribed
      string token
      datetime created_at
      datetime updated_at
    }

    %% ============================================
    %% EMPLOYEES & SERVICES (scheduling)
    %% ============================================
    EMPLOYEE {
      int id
      string name
      string home_address
    }

    SERVICECATEGORY {
      int id
      string name
    }

    TIMESLOT {
      int id
      string label
    }

    USER ||--o{ BOOKING : "creates → service request"
    EMPLOYEE ||--o{ BOOKING : "assigned to"
    SERVICECATEGORY ||--o{ BOOKING : "booked under"
    TIMESLOT ||--o{ BOOKING : "scheduled in"

    EMPLOYEE ||--o{ JOBASSIGNMENT : "has route assignments"
    BOOKING ||--o{ JOBASSIGNMENT : "creates job assignment"

    BOOKING {
      int id
      date date
      string service_address
      decimal unit_price
      decimal total_amount
      string status "Booked / Cancelled / Completed"
      datetime created_at
      datetime updated_at
    }

    JOBASSIGNMENT {
      int id
      string jobsite_address
    }

    %% ============================================
    %% CARTS & CHECKOUT (billing)
    %% ============================================
    USER ||--o{ CART : "owns → active cart"
    CART ||--o{ CARTITEM : "contains → items"
    SERVICECATEGORY ||--o{ CARTITEM : "references category"
    TIMESLOT ||--o{ CARTITEM : "selected slot"
    EMPLOYEE ||--o{ CARTITEM : "selected employee"

    CART {
      int id
      string session_key
      string address_key
      datetime created_at
      datetime updated_at
    }

    CARTITEM {
      int id
      string service_address
      date date
      decimal unit_price
      int quantity
      datetime created_at
    }

    %% ============================================
    %% PAYMENTS & CHAINS (billing)
    %% ============================================
    USER ||--o{ PAYMENTHISTORY : "makes → payments"
    USER ||--o{ PAYMENT : "initiates → Stripe payment"

    BOOKING ||--o| PAYMENTHISTORY : "primary_payment_record"
    PAYMENTHISTORY ||--o{ PAYMENTHISTORY : "adjustment chain (self-FK)"
    PAYMENTHISTORY ||--o{ BOOKING : "linked_bookings (M2M)"
    PAYMENTHISTORY ||--o| BOOKING : "primary booking FK"
    CART ||--o{ PAYMENTHISTORY : "originates from checkout"

    PAYMENTHISTORY {
      int id
      decimal amount
      decimal adjustments_total_amt
      string currency
      string status
      string payment_type
      string service_address
      string stripe_payment_id
      string notes
      datetime created_at
      json raw_data
    }

    PAYMENT {
      int id
      int amount
      string currency
      string stripe_payment_intent_id
      string stripe_checkout_session_id
      string status
      string description
      string receipt_url
      datetime created_at
      datetime updated_at
    }

    %% ============================================
    %% COLOR & STYLES BY APP
    %% ============================================
    classDef core fill:#E8F1FA,stroke:#0366d6,stroke-width:1px;
    classDef customers fill:#EBF8E1,stroke:#2da44e,stroke-width:1px;
    classDef scheduling fill:#FFF4E5,stroke:#f66a0a,stroke-width:1px;
    classDef billing fill:#FCE8EF,stroke:#d63384,stroke-width:1px;
    classDef legend fill:#f8f9fa,stroke:#adb5bd,stroke-dasharray: 2 2;

    class USER,ADDRESS,NEWSLETTERSUBSCRIPTION core
    class CUSTOMERPROFILE customers
    class EMPLOYEE,SERVICECATEGORY,TIMESLOT,BOOKING,JOBASSIGNMENT scheduling
    class CART,CARTITEM,PAYMENTHISTORY,PAYMENT billing
```

[View on Mermaid Live](https://mermaid.live/edit#pako:eNrFWN1O4zgUfhUro1kxUpilv4SO9qKUdKYDpagtu2KFFLmJ2xryN7Yz0AFu9wH2EfdJ9riN08ZNCjsgba-a2Ofz8edzvnOcB8ONPGK0DMJOKJ4xHFyHCH7v36Pf_sMvM7oc2cMR-gV1BkMbXQwH3d6ZjU7a4_YrYCUmenzc348eUPvkZGiPRqiFro3oLuTon7_-RkHiCxr7BGHPY4Rzwq8NzfTxEXUuR-NB3x4qryQEuRck9FYobsJFFBCGaDiNtgCiR3Ru_zE6s8dj2OHl8agz7F2Me4PzJc4ccxSSO-4TIQAhZmRKGAndlScrKOX6w-oRwToCUU89ccFoOEM-nhBff0dDUil4V9XeuVQstFdcYEG0d3EEb31HHrwOECWhYCnGk3JcJ273BuJ5FOq4JMDU31oriHGo-7tijhEP3AsFdoU2LmhAfmwvMKE-EDJz4JEQ4aRxUDKpgKa1_TZdauwHjQsoY2RGo1BnnbDv1CW73VGTik4ts992R40Vu6NG8255ACOZQy4j8NdzsNgaSmIvN5Qdf0nYl0SBBIFUuBcOh8xy1j5MoshHSciTCXcZnRA9bkR0S97G4Z_VLrt_cTa4sm2pX5D2v_c68HePu3PiJTICPrwCXmE_kzwhDvQTnYMm5SMo22jqZKc9tj8Phlcvxs4Axr2-PTobjF-uSZnppigfDwanvfPPSyVcHdhKUdNghBz5lhAulKZmXBSYY87pLCQehIOaru-ywApi6xZsktAjTJlleyuYn54pmNBwLdC6X18Hx-3RqPf5vG-fjzOZZ1ECEb7yMyChyGqNWqDUWlFzE0027NfrK4BdmeWVC4KmMh5xaYBlylHhxAxm6CMikmUAB1L0C8pGwsHn4xWzv6IOhmrm-6v_IN1Q6SCFjTdJ2DxVu2MRyONUlGXEz6Z-pz0cL9uWL3bndHA5Rnup6n94o75FLpBvWqC20e_AF2ZZYiwnbRj0xnZ_FTmyFtLUEHYf8GeSI2e9bkZgNUFmEVT4kiTJ2XHiExcODHE_Kk3eYgsCARItCFkH93Jvu48W-jYORcu5JXo9TA97c-RVAZc5_ZxDxZmlJ2J5qknYbwkOxUaNL_X81VF80b6SGbQK5HbvfPTmYZyu8KUHHSFEmzzzAN-mch_jRU4QCwyXFhRoolmRGAHXMVHG22qYNt8FKwPTAWYLJzWFnseNWKZJmkH5BrB3A52_REDuHLIMSj7xp_vd0w-7oTYLCnAMMunIOgRsc7TXr_Z3mj_mzNOdoNQedU-LJKHA94jRGQ2XXE5ZFMAGiHsLBWpNo2ZUVlvSCM4Xg-xtxhB3VNHQK4abMKkxi8JCojf56YGJRfzCYpahyVjJDny7xYmAiRcoxA2PQsTwnQNzsJZ8KlJLmJJPhSWzlIC8y6Eo9Dydps7PUVpYMLGAUI_InjoW2zcRyAkCA07C_P-1t-4MzgZD2VePr86gqz6-Qu2Li1dAuj50UCdkCtdIRtAUVK71zra6lW7bhJ1Dz9J6d1BrNr1m-rh_Rz0xb1Xi-086QHrt5wrluGvZlQyl6uF6nTyLsr4lpDDdbrduNzKYabOJD_CzMKlcK4yObdndDMNr1mpW_VkMn8zg5pVCTK3p0RRnENibNCaegvAwn2PG8KKFqqj6SZ3xEmmp3mb6zcIsuQNK8jdt9C8FGbebk1QHYWq9i6maETOVRjPfF64pzi0JAmmqem7m1U49KloN05gx6hktwRJiGuBYgOWjscz1a0PMCVyRDCmsHma3UkSfwCbG4Z9RFCgzuADM5kZrin0OT6tMSb-dZVOIvIl0pEoYrWr1sLEEMVoPxr3RsqyP1cPDSs06qlr16lHFNBYwyfrYODo8aNSbB9XDes1qPJnGj-WiBx-tSrV-2GhUas1G7aBhWU__Ah4VE_c)
---

[Back to Table of Contents](#table-of-contents)

## Apps Overview

* **scheduling** → bookings, availability
* **billing** → payments, cart
* **customers** → profiles
* **core** → user + address

### 📱 Responsive Design Strategy

The application follows a **mobile-first approach**, with layout and interaction patterns adapted based on screen size and input type.

#### Breakpoint Behavior

- At **992px and below**, all data-heavy table layouts are converted into **stacked card-based views**.
- This prevents horizontal compression and ensures content remains readable on smaller screens.
- The main navigation bar collapses into a **mobile-friendly hamburger menu** at this breakpoint.
- Above 992px, layouts expand into **multi-column grids and tables** for improved information density.

#### Mobile & Tablet (≤992px)

- Touchscreen devices do not reliably support drag-and-drop interactions.
- Booking interactions are adapted to use:
  - tap-based controls
  - vertically stacked actions
  - larger touch targets

- Tables are replaced with **card layouts** to improve:
  - readability
  - scanability
  - interaction clarity

- Navigation is simplified using a **collapsible hamburger menu**, improving usability on smaller screens.

- Forms and content use **single-column layouts** to avoid horizontal scrolling.

#### Desktop (>992px)

- Multi-column layouts and grids are used to maximise available screen space.
- Table views are restored where they remain readable and efficient.
- The full navigation bar is displayed, allowing direct access to all sections.
- Drag-and-drop interactions are supported for enhanced usability with mouse and trackpad input.
- Higher information density is maintained without compromising clarity.

#### Design Rationale

This approach ensures:

- consistent usability across device types
- clear data presentation at all screen sizes
- appropriate interaction models for both touch and pointer-based devices

[Back to Table of Contents](#table-of-contents)

## Scheduling App Overview

Customer-facing scheduling with **resource-aware availability**, **drag-and-drop booking**, and a **mini cart**.

Staff users have a dedicated dashboard providing visibility of their assigned upcoming bookings. Access is role-restricted, ensuring only authorized staff members can view operational schedules. Staff interactions are intentionally limited to viewing responsibilities, while booking modifications and cancellations remain controlled by customer workflows to preserve business integrity.

### Features
- **Two search modes (mutually exclusive):**
  - **Search by Date** → Show all time slots for that day.
  - **Search by Time Slot** → Show all dates where that slot has available resources.
- **Service Categories:** Garage/Basement, Lawncare, House Cleaning.
- **Resource pills per slot** (e.g., 5 employees → 5 pill buttons).
- **Travel adjacency logic:** show resources only if their jobs in adjacent slots are within ~30 minutes drive.
- **Drag & Drop to Cart:** resource pills dragged into cart; slot dims or hides when booked.
- **Mini Cart (always visible):** shows item count and total $; expandable with hamburger for itemized list and checkout.
- **Login/Signup required** to complete checkout and save purchase history.

### Reusability
- **Calendar grid** reusable across services.
- **Availability filter logic** (time + travel distance).
- **Drag-and-drop cart** reusable for other booking flows.
- **CSS variables** for consistent theme.

### How to Wire Into Another Project
1. Add `scheduling` to `INSTALLED_APPS` in `settings.py`
2. Include URLs in your project’s `urls.py`:
   ```python
   from django.urls import path, include

   urlpatterns = [
       path(
        "schedule/",
        include(("scheduling.urls", "scheduling"), namespace="scheduling"),
    ),
   ]
   ```


### 🖼️ Wireframes

Wireframes were created during the UX design phase to validate layout, search methods, and booking flow before coding.
Each wireframe corresponds to a key customer-facing screen.

**Search by Date**

  ![Search by Date Wireframe](readme/wireframes/scheduling-search-by-date.png)

- **Search by Time Slot**

  ![Search by Date Wireframe](readme/wireframes/scheduling-search-by-timeslot.png)

- **Search Results**

  ![Search Results Wireframe](readme/wireframes/search-results.png)

- **Employee Routes**

  ![Routes Image](readme/wireframes/map-of-routes.png)

- **Staff Dashboard**

![Staff Dashboard Wireframe](readme/wireframes/staff-dashboard.png)

[Back to Table of Contents](#table-of-contents)


## Billing App Overview

The **Billing app** manages financial transactions, including cart handling, checkout, payments, and invoice tracking.

It serves as the **financial layer of the system**, clearly separated from scheduling logic to ensure clean transaction processing and reporting.

### 🔑 Features

- Stripe checkout integration
- Idempotent payment handling (prevents duplicate transactions)
- Payment history grouped by service address
- Running invoice model (per property)
- Refund and cancellation workflow
- Adjustment tracking for bookings (add / cancel services)

### ♻️ Reusability

- Address-based invoice grouping model
- Payment tracking and adjustment workflow
- Transaction history structure for reporting
- Checkout validation and payment confirmation logic
- Separation of payment layer (`Payment`) and accounting layer (`PaymentHistory`)

### 🚀 How to Wire Into Another Project

1. Add `billing` to `INSTALLED_APPS` in `settings.py`
2. Include URLs in your project’s `urls.py`:

```python
   from django.urls import path, include

   urlpatterns = [
       path("billing/", include(("billing.urls", "billing"),
                             namespace="billing")),
   ]
```

---

### 🖼️ Wireframes

Wireframes were created during the UX design phase to validate layout and navigation before coding.
Each wireframe below corresponds to a key page in the **Billing App**.

- **Cart**

  ![Checkout Cart Wireframe](readme/wireframes/cart.png)

- **Payment History**

  ![Payment History Wireframe](readme/wireframes/payment-history.png)

- **Booking Adjustments**

  ![Booking Adjustments Wireframe](readme/wireframes/adjustments.png)

[Back to Table of Contents](#table-of-contents)

## Customers App Overview

The **Customers app** provides a reusable pattern for managing core business data in a Django project.
It implements **full CRUD (Create, Read, Update, Delete)** operations with a mobile-first, responsive UI.

### 🔑 Features

- Superuser-only access (owner-facing app).
- Customer search by name, address, or email.
- Pagination with "Showing X–Y of Z results" for clarity.
- Mobile-first layout, optimized for 412px screens and up.
- Custom global styling system with CSS variables for consistent theming.
- Reusable confirmation modal for destructive actions (delete).
- Extensible templates and views.

### ♻️ Reusability

This app was built as a **blueprint for future apps** (Scheduling, Employees, Inventory).

Key reusable elements include:
- **Model + Form pattern** with validation.
- **Search + pagination logic** for large datasets.
- **Mobile-first templates** that adapt across phases.
- **Global CSS variables** for consistent design across apps.
- **CRUD workflow with confirmation modals**.

By following this pattern, future apps (e.g., Employees, Scheduling, Inventory) can be quickly wired up using the same structure.

### 🚀 How to Wire Into Another Project (same for other apps)
1. Add `customers` to your `INSTALLED_APPS` in `settings.py`.
2. Include the app’s URLs:
   ```python
    path(
        "customers/",
        include(("customers.urls", "customers"), namespace="customers"),
    ),


### 🖼️ Wireframes

Wireframes were created during the UX design phase to validate layout and navigation before coding.
Each wireframe below corresponds to a key page in the **Customers App**.

---

- **Home / Navbar Mobile 412x844**
  - ![Home / Navbar Wireframe](readme/wireframes/home_navbar_mobile.png)

  - ![Home / Navbar Wireframe](readme/wireframes/home_navbar_larger_devices.png)

  - **Customer Profile** (customer facing page)

  ![Customer Profile Wireframe](readme/wireframes/profile.png)

---



[Back to Table of Contents](#table-of-contents)

## Core App Overview

The **Core app** provides shared functionality and foundational models used across the entire project.

It serves as the **system backbone**, supporting authentication, reusable data structures, and global features that are not tied to a single domain.

### 🔑 Features

- Django authentication integration (`User` model)
- Reusable `Address` model for general-purpose storage
- Newsletter subscription system
- Global layout and navigation handling
- Shared templates and base structure

### ♻️ Reusability

- Centralized base templates (`base.html`, layout structure)
- Shared context and UI components (navbar, footer)
- Reusable address model for non-transactional use
- Cross-app consistency for styling and layout
- Newsletter subscription pattern reusable across projects

### 🚀 How to Wire Into Another Project

1. Add `core` to your `INSTALLED_APPS` in `settings.py`.
2. Include the app’s URLs:
   ```python
    path("", include(("core.urls", "core"), namespace="core")),


[Back to Table of Contents](#table-of-contents)

## CRUD & Booking Lifecycle

### Table A — CRUD Operations Overview

| Operation | Scope | Behavior | Data Impact |
|----------|------|--------|------------|
| Create | Booking (Cart → Checkout) | New booking created after successful payment | Inserts Booking + PaymentHistory |
| Read | User / Admin views | Display bookings, invoices, payment history | No data modification |
| Update | Booking state | Status changes (active → cancelled → refunded) | Updates Booking + PaymentHistory |
| Delete | Draft services only | Pre-checkout items removed from cart | Deletes CartItem only |

### Table B — Booking State Transitions

| Current State | Action | Next State | Constraint |
|--------------|--------|----------|-----------|
| Draft | Checkout | Active | Payment must succeed |
| Active | Cancel | Cancelled | Cannot cancel twice |
| Cancelled | Refund | Refunded | Triggered via payment workflow |
| Any | Modify | Blocked | Past bookings cannot be changed |

### Table C — Validation & Constraints

| Rule | Enforcement | Outcome |
|-----|------------|--------|
| No past bookings | Server-side validation | Booking rejected |
| No double booking | Availability check | Slot blocked |
| No duplicate payment | Stripe idempotency | Duplicate prevented |
| No repeated cancellation | State check | Action denied |
| Cart consistency | Recalculation on change | Accurate totals |

User flow: drag → add → delete → totals dynamically recalculated

### Data Flow Diagram

```mermaid
flowchart TD

    %% =========================
    %% USER INPUT
    %% =========================
    A[User selects service, date, time slot, address]

    %% =========================
    %% VALIDATION
    %% =========================
    B[Validate input]
    B1{Valid?}
    B --> B1

    B1 -- No --> B_ERR[Return validation errors]
    B1 -- Yes --> C[Check availability]

    %% =========================
    %% CAPACITY & LOGIC
    %% =========================
    C --> C1{Slot & employee available?}
    C1 -- No --> C_ERR[Show unavailable / FULL]
    C1 -- Yes --> D[Select employee & route]

    %% =========================
    %% CART FLOW
    %% =========================
    D --> E[Add to CartItem]
    E --> F[Attach to Cart session or user]

    %% =========================
    %% CHECKOUT
    %% =========================
    F --> G[Proceed to checkout]
    G --> H[Create Stripe session]

    %% =========================
    %% PAYMENT
    %% =========================
    H --> I[User completes payment]
    I --> J[Stripe webhook / success return]

    %% =========================
    %% PERSISTENCE
    %% =========================
    J --> K[Create Payment record]
    K --> L[Create PaymentHistory entry]

    L --> M[Create Bookings]
    M --> N[Link Booking ↔ PaymentHistory]

    %% =========================
    %% POST-PROCESSING
    %% =========================
    N --> O[Mark slot as unavailable]
    O --> P[Update employee assignment]

    %% =========================
    %% OUTPUT
    %% =========================
    P --> Q[Show confirmation to user]
    Q --> R[Store for reporting / history]
```

[View on Mermaid Live](https://mermaid.live/edit#pako:eNqVVG1vokAQ_iubTa6fbOsLWmtyd6GISotARXvpoblQGIUIrFmW9jzj1_sF9wvvl9yygjVNLhE-ADv7PDvPzM7MDnvEB9zDy4i8eYFLGZr258k8Qfz59Al9_t9zRMxsdYI0w5pNzyXJziwFilKIwGMp_9LX0IMa8l3G3yyMAaURYTXk-j6FNF1U0vMk61pfnmqmcS7pznlyozD3jsJkk7FFYW7shP3rvlijy8sv3FqquWtwAzLIwfxDnUycCbCMJuj1cFxIEgSUEpouThnPkAqK4igBeGvkvrph5L6EUci21UJVZEtWtOkzukC6OdSUc6nKwX9jZ_M0czLEm4hsAUopEZQxK6cxKiJGOyBvKEuOUHSNBjNdX5wSyhD7ji0u-d3DBaIkY1A1zskUDXTz27mcvvCuOrLvI0aQwstaYxAXGlWxO3BkxlwvKAG8DtM0vzJCUcZrsqLEkao8mOf3wEBoGDoWJR6AUOnl1UCO5TcUiJGjUMgr02Y03EApspo4S34eq8bZ2kbCs3boUo_wqwPGL3TjbmNISnmaAN07ha43eAkIWfNiSDPP4yIRFb1QUag6sTV7qhqKei7rXuh4KNNkHURy7x6hfqH1QWD0D5hRmDJCt4j_0vfG0wV2XGLveFBhsio7eCx2DUcPk3W5h_7-_vPhzIpRm_b00pqYimrbmjE8l2kILaYzdulaDEzkpqeNWUg2BcxyZhsx4d57nRfSKilutIJaXuQVZr0lvD8epoZHkmVI48Nk5BVftFmOexQ4Pl14-gAteQ9S2BDK8vxeo6BIK67hFQ193GM0gxqOgR-WL_EuP2WOWQAxzHGP__o8K3M8T_acs3GT74TEJY1PoFWAe0s3SvkqE3nph-6KuvHRSiHxgSokSxjudW7FGbi3wz9xr9FqXzUlqdFq3EpSp9Xutmt4y83N5lW91Wjf3NxK9XpH6kr7Gv4l3NavOjfNltTstjrddqcrNff_ANVoFz8)

#### Data Flow Summary

The booking system follows a staged pipeline:

1. User input is validated before any state change
2. Availability and employee assignment are checked dynamically
3. Services are added to a cart before checkout
4. Stripe handles payment processing
5. Upon success, Payment and PaymentHistory records are created
6. Bookings are then persisted and linked to the payment record
7. System state is updated (availability, assignments)
8. Results are stored for reporting and user history

This flow ensures idempotent booking creation and prevents duplicate or invalid reservations.

The following section demonstrates how these CRUD operations behave under real-world conditions, including validation, state transitions, and edge-case handling.

## Booking Lifecycle & Defensive Programming

This section explains how the system enforces data integrity across the full booking lifecycle, building on the CRUD operations above to demonstrate real-world behavior, validation, and edge-case handling.

### Lifecycle Control

* active → cancelled → refunded
* No duplicate cancellation allowed
* Past bookings cannot be modified
* Booking state integrity enforced

---

The following scenarios demonstrate how these rules are enforced in real-world usage.

### Booking lifecycle — Standard Flow

The standard booking workflow was tested from initial selection through payment and persistence.

#### **Flow Covered**

This flow validates the full transaction pipeline from user interaction through to persistent storage and administrative visibility.


- Booking creation
- Cart population
- Checkout process
- Successful payment
- Persistence to payment history and admin

#### **Evidence**

- Booking Created — Before ![Booking Created — Before](./images/testing_screenshots/PASS_4/booking_lifecycle/01-booking-created-before.png)

- Booking Created — After ![Booking Created — After](./images/testing_screenshots/PASS_4/booking_lifecycle/02-booking-created-after.png)

- Go to Checkout ![Go to Checkout](./images/testing_screenshots/PASS_4/booking_lifecycle/03-booking-created-go-to-checkout.png)

- Checkout Summary ![Checkout Summary](./images/testing_screenshots/PASS_4/booking_lifecycle/04-booking-created-checkout-summary.png)

- Checkout Payment ![Checkout Payment](./images/testing_screenshots/PASS_4/booking_lifecycle/05-booking-created-checkout.png)

- Payment Success — History ![Payment Success — History](./images/testing_screenshots/PASS_4/booking_lifecycle/06-booking-success-payment-history.png)
- Invoice Generated ![Invoice Generated](./images/testing_screenshots/PASS_4/booking_lifecycle/07-booking-invoice.png)

---

### 🔁 Booking Adjustments & Cancellation

The system supports lifecycle updates including cancellation and financial adjustments.

#### Evidence

- Invoice After Cancellation ![Invoice After Cancellation](./images/testing_screenshots/PASS_4/booking_lifecycle/08-booking invoice after cancellation.png)
- Payment History After Cancellation ![Payment History After Cancellation](./images/testing_screenshots/PASS_4/booking_lifecycle/09-booking - payment history after cancellation.png)

---

### 🔁 Rebooking Workflow

Rebooking scenarios were tested to ensure system consistency and correct state handling.

#### Evidence

- Rebooking — Before ![Rebooking — Before](./images/testing_screenshots/PASS_4/booking_lifecycle/10-rebooking-created-before.png)

- Rebooking — After ![Rebooking — After](./images/testing_screenshots/PASS_4/booking_lifecycle/11-rebooking-created-after.png)

- Rebooking — Checkout Summary ![Rebooking — Checkout Summary](./images/testing_screenshots/PASS_4/booking_lifecycle/12-rebooking-created-checkout-summary.png)

- Rebooking — Checkout ![Rebooking — Checkout](./images/testing_screenshots/PASS_4/booking_lifecycle/13-rebooking-created-checkout.png)

- Rebooking — Payment Success ![Rebooking — Payment Success](./images/testing_screenshots/PASS_4/booking_lifecycle/14-rebooking-success-payment-history.png)

- Rebooking — Invoice ![Rebooking — Invoice](./images/testing_screenshots/PASS_4/booking_lifecycle/15-rebooking-invoice.png)

---

### 🧑‍💼 Admin & System Verification

Bookings and payments were verified from the administrative perspective.

#### Evidence

- Admin Payment History ![Admin Payment History](./images/testing_screenshots/PASS_4/booking_lifecycle/16-admin-payment-history.png)

- Admin Booking History ![Admin Booking History](./images/testing_screenshots/PASS_4/booking_lifecycle/17-admin-booking-history.png)

---
[Back to Table of Contents](#table-of-contents)

### 🛡️ Defensive Programming — Input Validation

The system prevents invalid or logically inconsistent user actions.
All validation rules are enforced server-side to ensure data integrity regardless of client behavior.

#### Scenarios Tested
- Booking in the past
- Missing required address input

#### Evidence

- Past Date Search Attempt ![Past Date Search Attempt](./images/testing_screenshots/PASS_4/booking_lifecycle/18-past-date-search.png)

- Past Date Booking Denied ![Past Date Booking Denied](./images/testing_screenshots/PASS_4/booking_lifecycle/19-past-date-booking-denied.png)

- Empty Address Search Denied ![Empty Address Search Denied](./images/testing_screenshots/PASS_4/booking_lifecycle/20-empty-address-search-denied.png)

---

## 🛡️ Defensive Programming — Availability Integrity

The system ensures that availability is correctly managed across cart and payment states. Availability is recalculated at each stage to prevent race conditions between cart state and confirmed bookings.

### Scenarios Tested

- Availability before booking
- Reservation during cart stage
- Final confirmation after payment

### Evidence

- Timeslot Available Before Payment

![Timeslot Available Before Payment](./images/testing_screenshots/PASS_4/booking_lifecycle/21-timeslot-available-before-payment.png)

- Timeslot Added to Cart

![Timeslot Added to Cart](./images/testing_screenshots/PASS_4/booking_lifecycle/22-timeslot-in-cart.png)

- Timeslot Payment

![Timeslot Payment](./images/testing_screenshots/PASS_4/booking_lifecycle/23-payment-for-timeslot.png)

- Timeslot in Payment History

![Timeslot in Payment History](./images/testing_screenshots/PASS_4/booking_lifecycle/24-timeslot-in-payment-history.png)

- Timeslot in Admin Payment History

![Timeslot in Admin Payment History](./images/testing_screenshots/PASS_4/booking_lifecycle/25-timeslot-in-admin-payment-history.png)

- Timeslot in Admin Bookings

![Timeslot in Admin Bookings](./images/testing_screenshots/PASS_4/booking_lifecycle/26-timeslot-in-admin-bookings.png)

---

## 🛡️ Defensive Programming — Double Booking Prevention

The system prevents duplicate bookings for the same time slot. This is enforced through backend validation checks against existing confirmed bookings for the same resource and time slot.

### Evidence

- Search Same Timeslot After Booking ![Search Same Timeslot After Booking](./images/testing_screenshots/PASS_4/booking_lifecycle/27-search-same-timeslot-on-same-day-after-booking.png)

---

## 🛡️ Defensive Programming — Concurrent Checkout Protection

The system prevents duplicate or conflicting transactions across multiple browser sessions or tabs. Concurrency control ensures that only one successful transaction can be completed per booking instance across multiple sessions.

### Scenarios Tested
- Checkout initiated in one tab
- Duplicate checkout attempt in second tab
- System blocking duplicate transaction

### Evidence

- Checkout Summary ![Checkout Summary](./images/testing_screenshots/PASS_4/booking_lifecycle/28-checkout-summary.png)

- Checkout Tab A ![Checkout Tab A](./images/testing_screenshots/PASS_4/booking_lifecycle/29-checkout-on-tab-A.png)

- Duplicate Checkout Created ![Duplicate Checkout Created](./images/testing_screenshots/PASS_4/booking_lifecycle/30-create-duplicate-checkout-tab-B.png)

- Checkout Success Tab A ![Checkout Success Tab A](./images/testing_screenshots/PASS_4/booking_lifecycle/31-checkout-success-tab-A.png)

- Duplicate Attempt Tab B ![Duplicate Attempt Tab B](./images/testing_screenshots/PASS_4/booking_lifecycle/32a-attempt-checkout-on-duplicate-tab-B.png)

- Duplicate Checkout Blocked ![Duplicate Checkout Blocked](./images/testing_screenshots/PASS_4/booking_lifecycle/32b-checkout-on-duplicate-tab-B-blocked.png)

---

## 🛡️ Defensive Programming — Payment Failure Handling

The system correctly handles failed payment scenarios and prevents inconsistent states. Failed transactions do not persist booking records, ensuring the system remains in a consistent and recoverable state.

### Evidence

- Declined Payment — Before ![Declined Payment — Before](./images/testing_screenshots/PASS_4/booking_lifecycle/34-declined-card-payment-back-to-checkout-summary-before.png)

- Declined Attempt — Before ![Declined Attempt — Before](./images/testing_screenshots/PASS_4/booking_lifecycle/34a-declined-card-payment-attempt-before.png)

- Declined Attempt — After ![Declined Attempt — After](./images/testing_screenshots/PASS_4/booking_lifecycle/34b-declined-card-payment-attempt-after.png)

---

### 🧠 Summary

The booking system demonstrates:

- full lifecycle integrity from booking to payment
- correct persistence across user and admin views
- protection against invalid inputs and edge cases
- prevention of duplicate bookings and race conditions
- robust handling of failed payment scenarios

These tests confirm that the system behaves reliably under both normal and adverse conditions. The results demonstrate robust handling of both expected user flows and edge-case scenarios under real-world conditions.

[Back to Table of Contents](#table-of-contents)

## Functional Testing

All tests were conducted using valid Greater Dallas addresses to ensure realistic availability results.

## VT-10A — Functional Testing (Authentication & Account Workflow)

Manual functional testing was conducted to verify the authentication and account lifecycle from registration through logout, including email flows, profile updates, admin verification, and access control.

### Scope

Testing covered:

- new user signup
- inbox / verification flow
- welcome and newsletter email delivery
- successful authenticated landing
- profile completion and update
- admin-side verification of created and updated user records
- logout flow
- access control for protected views

---

### Detailed Results

| Test ID | Area | File / Page | Expected | Result |
|---|---|---|---|---|
| VT-10A.1 | Authentication | Signup | New user account can be created successfully | Pass |
| VT-10A.2 | Authentication | Check Inbox | Verification / follow-up email prompt shown correctly | Pass |
| VT-10A.3 | Authentication | Welcome Email | Welcome email delivered after signup | Pass |
| VT-10A.4 | Authentication | Newsletter Email | Newsletter signup email delivered for first-time user | Pass |
| VT-10A.5 | Authentication | Email Verification | Verification messaging shown correctly | Pass |
| VT-10A.6 | Authentication | Customer Home Page | Authenticated user is redirected into valid logged-in state | Pass |
| VT-10A.7 | Authentication | Admin Verification (new user) | Newly created user appears correctly in admin | Pass |
| VT-10A.8 | Authentication | Profile Update (before) | Existing account data visible before update | Pass |
| VT-10A.9 | Authentication | Profile Update | User profile information updates successfully | Pass |
| VT-10A.10 | Authentication | Admin Verification (updated user) | Updated user details are reflected in admin | Pass |
| VT-10A.11 | Authentication | Logout Action | User can log out successfully | Pass |
| VT-10A.12 | Authentication | Post-Logout Home Page | Logged-out state is shown correctly | Pass |
| VT-10A.13 | Authentication | Access Control 1 | Protected route is blocked for unauthorized user | Pass |
| VT-10A.14 | Authentication | Access Control 2 | Restricted content is not exposed without proper login | Pass |
| VT-10A.15 | Authentication | Access Control 3 | Additional protected view correctly redirects or denies access | Pass |
| VT-10A.16 | Authentication | Access Control 4 | Role/session protection behaves correctly under direct access attempt | Pass |

---

### Evidence

- VT-10A.1

![Signup](./images/testing_screenshots/Authentication/01-Signup.png)

- VT-10A.2

![Check Inbox](./images/testing_screenshots/Authentication/02-Check-Inbox.png)

- VT-10A.3

![Welcome Email](./images/testing_screenshots/Authentication/03-Welcome-email.png)

- VT-10A.4

![Newsletter Email](./images/testing_screenshots/Authentication/04-Newsletter-email.png)

- VT-10A.5

![Email Verification Message](./images/testing_screenshots/Authentication/05-Email-verification-message.png)

- VT-10A.6

![Customer Home Page](./images/testing_screenshots/Authentication/06-Customer-home-page.png)

- VT-10A.7

![New User in Admin](./images/testing_screenshots/Authentication/07-New-user-in-admin.png)

- VT-10A.8

![Update User Profile — Before](./images/testing_screenshots/Authentication/08-Update-user-profile-before.png)

- VT-10A.9

![Update User Profile Info](./images/testing_screenshots/Authentication/09-Update-user-profile-info.png)

- VT-10A.10

![User Info in Admin Updated](./images/testing_screenshots/Authentication/10-User-info-in-admin-updated.png)

- VT-10A.11

![User Logout](./images/testing_screenshots/Authentication/11-User-logout.png)

- VT-10A.12

![Logout Home Page](./images/testing_screenshots/Authentication/12-Logout-home-page.png)

- VT-10A.13

![Access Control 1](./images/testing_screenshots/Authentication/13-Access-control-1.png)

- VT-10A.14

![Access Control 2](./images/testing_screenshots/Authentication/13-Access-control-2.png)

- VT-10A.15

![Access Control 3](./images/testing_screenshots/Authentication/13-Access-control-3.png)

- VT-10A.16

![Access Control 4](./images/testing_screenshots/Authentication/13-Access-control-4.png)

---

### Summary

Authentication testing confirmed that secure access control and authentication boundaries are correctly enforced across the application.

- new users can register successfully
- email-based onboarding and verification workflows function correctly
- first-time users are enrolled into the newsletter workflow as designed
- profile updates persist correctly
- admin records reflect user creation and updates accurately
- logout returns the application to a valid unauthenticated state
- protected routes remain inaccessible without proper authentication

[Back to Table of Contents](#table-of-contents)

## VT-10B — Functional Testing (Booking & Checkout Workflow)

Manual testing validates the authentication and account lifecycle to validate the full booking workflow from service selection through checkout, payment, and persistence.

### Scope

Testing covered:

- service search and availability display
- adding bookings to cart
- checkout process
- successful payment handling
- booking persistence in user and admin views

---

### Detailed Results

| Test ID | Area | File / Page | Expected | Result |
|---|---|---|---|---|
| VT-10B.1 | Booking | Search results | Available services displayed correctly | Pass |
| VT-10B.2 | Booking | Add to cart | Selected service added to cart | Pass |
| VT-10B.3 | Booking | Cart state | Cart reflects selected booking | Pass |
| VT-10B.4 | Checkout | Checkout summary | Booking details displayed correctly | Pass |
| VT-10B.5 | Checkout | Payment process | Payment completes successfully | Pass |
| VT-10B.6 | Booking | Payment history | Booking stored and displayed | Pass |
| VT-10B.7 | Booking | Invoice generation | Invoice generated correctly | Pass |
| VT-10B.8 | Admin | Admin booking view | Booking visible in admin panel | Pass |

---

### Evidence

- VT-10B.1

![Booking Created — Before](./images/testing_screenshots/PASS_4/booking_lifecycle/01-booking-created-before.png)

- VT-10B.2

![Booking Created — After](./images/testing_screenshots/PASS_4/booking_lifecycle/02-booking-created-after.png)

- VT-10B.3

![Go to Checkout](./images/testing_screenshots/PASS_4/booking_lifecycle/03-booking-created-go-to-checkout.png)

- VT-10B.4

![Checkout Summary](./images/testing_screenshots/PASS_4/booking_lifecycle/04-booking-created-checkout-summary.png)

- VT-10B.5

![Checkout Payment](./images/testing_screenshots/PASS_4/booking_lifecycle/05-booking-created-checkout.png)

- VT-10B.6

![Payment Success — History](./images/testing_screenshots/PASS_4/booking_lifecycle/06-booking-success-payment-history.png)

- VT-10B.7

![Invoice Generated](./images/testing_screenshots/PASS_4/booking_lifecycle/07-booking-invoice.png)

- VT-10B.8

![Admin Booking View](./images/testing_screenshots/PASS_4/booking_lifecycle/17-admin-booking-history.png)

---

### Summary

Booking workflow testing confirmed that transactional integrity is maintained from service selection through checkout, payment, and persistence.

- services can be selected and added to cart correctly
- checkout process reflects accurate booking data
- payments are processed successfully
- bookings persist correctly across user and admin views
- invoices are generated and accessible

---
[Back to Table of Contents](#table-of-contents)

## UX & Design

### **Responsive Design**

At mobile width (412px), drag-and-drop interaction was not reliable because touch gestures favored page scrolling. A tap/click add-to-cart fallback was therefore treated as the preferred mobile interaction pattern.

A mobile/tablet-safe Add to Cart interaction was added for search results. Drag-and-drop remains available on desktop, while touch-width layouts use explicit Add to Cart buttons to avoid scroll interference on smaller devices. This improves usability across responsive breakpoints.

### **Mobile UX Optimization**

* Card-based layouts for invoices
* No horizontal scrolling
* Tap-to-add replaces drag on mobile
* Consistent UI patterns across views

The application was specifically optimized for mobile usability rather than relying solely on responsive tables.

### Key Improvements

#### **1. Mobile-first invoice and payment views**

- Replaced complex tables with **vertical card layouts** on smaller screens
- Each service/payment is displayed as a **stacked, readable block**
- Eliminates horizontal scrolling entirely

#### **2. Conditional layout rendering**
- Desktop (`≥992px`): full tables for data density
- Mobile/tablet (`<992px`): card-based layout for readability

#### **3. Touch-friendly interactions**
- Buttons expanded to full width on mobile
- Removed reliance on drag-and-drop for small screens
- Introduced explicit "Add to Cart" actions

#### **4. Consistent UI patterns**
- Same card structure used across:
  - Live Invoice
  - Payment History
  - Booking flows
- Standardized:
  - spacing
  - badges
  - action buttons

#### **5. Defensive UX improvements**
- Prevented duplicate bookings through:
  - server-side validation
  - real-time availability updates
- Blocked booking of past dates at checkout

### Result

Users can:
- Browse services
- Book appointments
- Review invoices
- Manage cancellations

...entirely on mobile without layout issues, scrolling conflicts, or interaction friction.

[Back to Table of Contents](#table-of-contents)

---

## Authentication & Access Control

The system implements authenticated user access and profile-based data management.

- User authentication handled via Django Allauth
- Email verification required before access to protected features
- Key views protected using:
  - `@login_required`
  - `@verified_email_required`

Users can:

* manage bookings
* track payments
* reuse stored data

Restricted functionality includes:
- booking services
- accessing checkout
- viewing payment history
- managing invoices

Unauthenticated users are redirected to login.

### User Profile Management

Each user has an associated `CustomerProfile` containing:

- billing address
- contact details (email, phone)
- service address history

Profile data is reused across the system:
- prefilled email in Stripe Checkout
- billing reference for invoices
- service address grouping for bookings

This reduces user friction and improves data consistency.

---

### User-Linked Data Integrity

All core data is linked to the authenticated user:

- bookings → linked to user account
- cart → user-specific session + DB
- payments → stored in `PaymentHistory`
- invoices → grouped by service address per user

This ensures:
- users can only access their own data
- full traceability of bookings and payments
- structured invoice history for reporting

---

### Result

Users can:
- securely manage bookings
- track payments per property
- reuse profile data for faster checkout

All actions are tied to authenticated identity and validated server-side.

[Back to Table of Contents](#table-of-contents)
---

## Deployment

Note: This deployment workflow is consistent across projects and has been adapted here for this application.

### Platform

* Heroku (PaaS)
* Neon PostgreSQL
* Namecheap domain
* Brevo email

### Custom Domain

👉 https://www.tuckeranddales.com

* SSL via Let's Encrypt
* DNS configured via Namecheap
* Config Vars used for production

### Setup

#### 1. **Clone repository**

```bash
git clone https://github.com/Pacman0126/tucker-and-dales-home-services.git

cd tucker-and-dales-home-services
```
#### 2. **Setup Database**

#### **Database Setup (Neon.tech PostgreSQL)**

We use Neon.tech for serverless PostgreSQL hosting (scalable, free tier available, branch-based dev/prod separation).

#### **Step-by-Step: Getting Your `DATABASE_URL`**

**A.  Log in to Neon Console**
   Go to https://console.neon.tech/ and sign in (use your email, GitHub, or Google account).

**B.  Select or Create Your Project**
   - If you already have a project: From the dashboard, click on your project name (e.g., "gambinos-restaurant-db").
   - If new: Click **Create project** → Enter a name → Choose Postgres version → Select region → Provide initial database name (e.g., "gambinos") → Click **Create project**.

**C.  Open Connection Details**
   On your **Project Dashboard**, click the **Connect** button (prominent blue/green button near the top or in the Connection Details widget).

**D.  Configure and Copy the Connection String**
   In the **Connect to your database** modal that opens:
   - **Branch**: Select your branch (usually "main" for production; create dev branches later if needed).
   - **Compute**: Leave default (Neon auto-scales).
   - **Database**: Select your database name (e.g., "neondb" or the one you created).
   - **Role/User**: Select the role (default is often your project owner or "neondb_owner").
   - The **full connection string** (DATABASE_URL) will auto-generate in the box below.
     It looks like: postgresql://neondb_owner:YOUR_LONG_PASSWORD@ep-your-project-name-123456.us-east-2.aws.neon.tech/your_db_name?sslmode=require

- Click **Copy** (or the clipboard icon) to copy the entire string.

**E.  Add to Your .env File**
Paste it into your project's `.env` (at root, next to manage.py):
- DATABASE_URL=postgresql://neondb_owner:YOUR_LONG_PASSWORD@ep-your-project-name-123456.us-east-2.aws.neon.tech/your_db_name?sslmode=require

- Replace with your actual copied value.
- **Security note**: Never commit `.env` to Git (it's in `.gitignore`). On Heroku, add this as a **Config Var** instead (Settings → Config Vars → Add key `DATABASE_URL` with the value).

**F.  Verify It Works Locally**
- Save `.env` and restart your server (`python manage.py runserver`).
- Run migrations: `python manage.py migrate` (should connect without errors).
- Or test in shell:

from django.db import connection
connection.ensure_connection()  # No error = success


#### **Important Notes**

- **Password security**: The password is embedded in the `DATABASE_URL` — if compromised, rotate it in Neon dashboard (Project → Settings → Users & roles → Edit role → Regenerate password → Update `.env`/Heroku).

- **Pooled vs. Direct**: Use the **direct** (non-pooled) string unless your app needs pooling (most Django apps work fine with direct). Avoid checking "Pooled connection" in the modal if offered.

- **SSL**: Neon requires `?sslmode=require` — it's included by default.

- **Multiple branches**: For dev/testing, create a branch in Neon → Get a separate `DATABASE_URL` → Use env-specific `.env` files or Heroku review apps.

- **Troubleshooting**: Connection errors? Check Neon dashboard → **Operations** tab for logs. Common fixes: Wrong branch/db name, expired password, or firewall (Neon allows all IPs by default).

This integrates with your `settings.py` (uses `env.db("DATABASE_URL")` fallback to local SQLite if missing).
---

[Back to Table of Contents](#table-of-contents)

## Website Domain and Email Host Deployment

using namecheap.com & Brevo.com

---
### Setup Website Domain

- Sign In/Sign Up to namecheap.com. Search for an available domain and purchase domain

![Alt text](./images/readme/namecheap/1-namecheap-search-domain.png)

![Alt text](./images/readme/namecheap/2-namecheap-buy-domain.png)

- Setup the DNS for your domain

![Alt text](./images/readme/namecheap/3-namecheap-setup-dns.png)

- Verify Contacts (email is sent to your email)

![Alt text](./images/readme/namecheap/4-namecheap-verify-contacts.png)

![Alt text](./images/readme/namecheap/5-namecheap-verify.png)

---
- Setup Brevo account with this domain and authenticate in Brevo via namecheap. Afterwards, check Advanced DNS settings from namecheap. If authentication is successful, Brevo will populate these settings automatically.

![Alt text](./images/readme/namecheap/6-namecheap-manage-domain.png)

![Alt text](./images/readme/namecheap/7-namecheap-manage-advanced-dns.png)

![Alt text](./images/readme/namecheap/8-advanced-dns.png)
---

[Back to Table of Contents](#table-of-contents)

### Setup Email Host (Brevo.com)

- Sign in/ or signup Brevo account to use the namecheap.com domain for email features

![Alt text](./images/readme/Brevo/1-brevo-home.png)

- Navigate plans and find free plan or whatever paid plan that fits your needs

![Alt text](./images/readme/Brevo/2-brevo-free-plan.png)

- Navigate to 'Domains' tab in 'Senders, Domains & Dedicated IP's'. Click 'Add Domain'

![Alt text](./images/readme/Brevo/3-brevo-settings-add-domain.png)

- Search and select an available domain. Click 'Add a domain'

![Alt text](./images/readme/Brevo/4-brevo-settings-add-domain-modal.png)

- In pop-up modal select Recommended option and click 'Continue'

![Alt text](./images/readme/Brevo/5-brevo-settings-authenticate-domain-modal.png)

- In pop-up modal give your namecheap.com credentials and click 'Continue'. This will look for your domain and transfer required records to namecheap.com when authentication succeeds.

![Alt text](./images/readme/Brevo/6-bevo-settings-continue-with-namecheap-login-modal.png)

- Senders, Domains & Dedicated IP's -> 'Domains' tab should now show a status of 'Authenticated'. This could take a few minutes or even longer.

![Alt text](./images/readme/Brevo/7-brevo-settings-domain-authentication-successful.png)

- Navigate to Senders, Domains & Dedicated IP's -> 'Settings' tab and click 'Add sender'

![Alt text](./images/readme/Brevo/8-brevo-add-sender.png)

- Add 'From Name' and 'From Email' and click 'Add sender'

![Alt text](./images/readme/Brevo/9-brevo-add-sender-step.png)

- Navigate to Senders, Domains & Dedicated IP's -> 'Senders' tab and see if everything is verified.

![Alt text](./images/readme/Brevo/10-brevo-add-sender-success.png)

- Navigate to 'Settings' -> 'SMTP & API' -> 'SMTP' tab to see current SMTP settings. Click on 'Generate a new SMTP key'

![Alt text](./images/readme/Brevo/11-brevo-smtp-api.png)

- In following pop-up modal, click 'Generate'. Copy and save SMTP key. This will go in your .env file.

![Alt text](./images/readme/Brevo/12-brevo-generates-smtp-key.png)

[Back to Table of Contents](#table-of-contents)

## Deployment (Heroku)

This project uses [Heroku](https://www.heroku.com), a platform as a service (PaaS) that enables developers to build, run, and operate applications entirely in the cloud.

Deployment steps are as follows, after account setup:

- Select **New** in the top-right corner of your Heroku Dashboard, and select **Create new app** from the dropdown menu.
- Your app name must be unique, and then choose a region closest to you (EU or USA), then finally, click **Create App**.
- From the new app **Settings**, click **Reveal Config Vars**, and set the value of **KEY** to `PORT`, and the **VALUE** to `8000` then select **ADD**.
- Further down, to support dependencies, select **Add Buildpack**.
- The order of the buildpacks is important; select `Python` first, then `Node.js` second. (if they are not in this order, you can drag them to rearrange them)

Heroku needs some additional files in order to deploy properly.

- [requirements.txt](requirements.txt)
- [Procfile](Procfile)
- [.python-version](.python-version)

You can install this project's **[requirements.txt](requirements.txt)** (*where applicable*) using:

- `pip3 install -r requirements.txt`

If you have your own packages that have been installed, then the requirements file needs updated using:

- `pip3 freeze --local > requirements.txt`


### Create Procfile

Create a `Procfile` in the root of the project to tell Heroku how to run the Django application.

Example:

```bash
echo web: gunicorn tucker_and_dales_home_services.wsgi > Procfile
```

The Procfile should contain:

```
web: gunicorn tucker_and_dales_home_services.wsgi
```


The **[.python-version](.python-version)** file tells Heroku the specific version of Python to use when running your application.

- `3.12` (or similar)

For Heroku deployment, follow these steps to connect your own GitHub repository to the newly created app:

Either (*recommended*):

- Select **Automatic Deployment** from the Heroku app.

Or:

- In the Terminal/CLI, connect to Heroku using this command: `heroku login -i`
- Set the remote for Heroku: `heroku git:remote -a app_name` (*replace `app_name` with your app name*)
- After performing the standard Git `add`, `commit`, and `push` to GitHub, you can now type:
    - `git push heroku main`

The Python terminal window should now be connected and deployed to Heroku!

- If not available register and sign up for a Heroku account
- From dashboard click "Create New App" and enter name of app

    ![Alt text](./images/readme/Heroko-dashboard-create-new-app.PNG)

- Name the app, select region, click "Create app"

    ![Alt text](./images/readme/Heroko-create-app.PNG)

- Name the app, select region, click "Create app"

    ![Alt text](./images/readme/Heroko-connect-app-to-github-repository.png)

---
### Django SECRET_KEY

- This is Django's cryptographic signing key. It **must** be unique and secret per environment.
- Locally this goes into .env file. In Heroku, this goes into Cofig Vars

- Generate a secure one:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(50))"


**Heroku Config Vars**
![Heroku Config Vars](./images/readme/heroku-config-vars.jpg)

**Live Deployment**
![Heroku Deployment](./images/readme/heroku-deployment.jpg)

---

- Click Github, search for your Github repository

    ![Alt text](./images/readme/Heroko-connect-app-to-github-repository.PNG)

- Using this already deployed app as an example, on the dashboard click on "Settings" and navigate  to "Buildpacks and add these items in this order while clicking "Add buildpack".

    ![Alt text](./images/readme/Heroko-settings-buildpacks.PNG)

- By now you should be connected to Github, select "Deploy" from dashboard, and then click "Deploy branch" from "Manual deploy" section

    ![Alt text](./images/readme/Heroko-deploy-app.PNG)

- Once successfully deployed, open app in browser terminal

    ![Alt text](./images/readme/Heroku-once-deployed-open-app.PNG)

---

[Back to Table of Contents](#table-of-contents)

## Custom Domain & Deployment Configuration

The application is deployed on Heroku and configured with a custom domain:

👉 https://www.tuckeranddales.com

---

### 🔧 Domain Setup

A custom domain purchased via Namecheap was connected to the Heroku application:

- Domain: `tuckeranddales.com`
- Subdomain: `www.tuckeranddales.com`
- DNS configuration:
  - `www` → CNAME → Heroku DNS target
  - Root domain → ALIAS/ANAME → Heroku DNS target

---

### 🔐 HTTPS / SSL

- SSL enabled using Heroku Automatic Certificate Management
- Certificate issued via Let's Encrypt
- Secure HTTPS enforced across the application

---

### ⚙️ Environment Configuration

Production settings configured via Heroku Config Vars:

- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `SITE_BASE_URL`

These ensure:
- Valid host header handling (prevents `DisallowedHost` errors)
- Secure form submissions
- Correct URL generation in emails and redirects

---

### ⚠️ Troubleshooting & Defensive Setup

During deployment, several issues were identified and resolved:

- `DisallowedHost` errors due to missing domain in `ALLOWED_HOSTS`
- SSL validation failures due to incorrect DNS configuration
- 400 Bad Request errors caused by misaligned domain settings

These were resolved through:
- Correct DNS configuration
- Updating environment variables
- Restarting Heroku dynos after configuration changes

---

### ✅ Outcome

- Application is fully accessible via custom domain
- HTTPS is active and verified
- Email links and redirects use the production domain
- SEO components (robots.txt, sitemap.xml) resolve correctly

### Google Maps API Setup

This project uses **two separate Google Maps API keys**:

- `GOOGLE_MAPS_BROWSER_KEY` for front-end map rendering
- `GOOGLE_MAPS_SERVER_KEY` for backend routing and availability checks

#### 1. Create a Google Cloud project
- Go to the Google Cloud Console
- Create or select a project
- Enable billing if required

#### 2. Enable the required APIs
Enable the following APIs for the project:

- Maps JavaScript API
- Directions API
- Distance Matrix API
- Geocoding API

#### 3. Create the browser key
Create an API key for front-end usage and store it as:


GOOGLE_MAPS_BROWSER_KEY=your_browser_maps_key

**Apply these restrictions:**

Application restriction: Websites

Add referrers such as:
- http://localhost:8000/*
- [tucker-and-dales-home-services-51862a9ae5a8.herokuapp.com](https://tucker-and-dales-home-services-51862a9ae5a8.herokuapp.com/*) (or https://your-heroku-app.herokuapp.com/*)
- https://tuckeranddales.com/*
- https://www.tuckeranddales.com/*

Restrict this key to:

Maps JavaScript API

#### 4. Create the server key

**Create a second API key for backend requests and store it as:**

GOOGLE_MAPS_SERVER_KEY=your_server_maps_key

Apply these restrictions:

- Application restriction: None
- API restriction: restrict the key to:
- Directions API
- Distance Matrix API
- Geocoding API

Do not apply website referrer restrictions to the server key, or backend availability searches will fail.

#### 5. Add both keys to environment variables

**Add both keys to your local .env file and to your deployed environment (for example, Heroku Config Vars).**


GOOGLE_MAPS_BROWSER_KEY=your_browser_maps_key
GOOGLE_MAPS_SERVER_KEY=your_server_maps_key

For deployment (e.g., Heroku), add them as Config Vars:

- heroku config:set GOOGLE_MAPS_BROWSER_KEY=your_browser_maps_key
- heroku config:set GOOGLE_MAPS_SERVER_KEY=your_server_maps_key

#### 6. Restart the application and test

After adding or updating the keys: heroku restart

Then verify:

- Search by date / time slot returns results
- Employee availability is displayed correctly
- “View Routes” loads Google Maps without errors

If issues occur, check browser console and server logs for:

- RefererNotAllowedMapError → incorrect browser key domain restrictions
- REQUEST_DENIED → missing API enablement or billing issue
- API keys with referer restrictions cannot be used with this API → server key incorrectly restricted

### Sample `.env`

```
# =====================================================
# Django Core
# =====================================================
SECRET_KEY=django-insecure-change-this-in-production
SITE_ID=1

# =====================================================
# Database (Neon PostgreSQL)
# Get from Neon Console -> Project -> Connect
# =====================================================
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require&channel_binding=require

# =====================================================
# Environment Flags
# =====================================================
DEBUG=False
DJANGO_PRODUCTION=False
LOCAL_NO_MANIFEST=True
USE_CONSOLE_EMAIL=False

# =====================================================
# Hosts / CSRF / Site URL
# Comma-separated values where applicable
# =====================================================
ALLOWED_HOSTS=127.0.0.1,localhost,0.0.0.0,.herokuapp.com,tucker-and-dales-home-services-51862a9ae5a8.herokuapp.com,tuckeranddales.com,www.tuckeranddales.com

CSRF_TRUSTED_ORIGINS=http://127.0.0.1,http://127.0.0.1:8000,http://localhost,http://localhost:8000,https://www.tuckeranddales.com,https://tuckeranddales.com

SITE_BASE_URL=https://www.tuckeranddales.com
ACCOUNT_DEFAULT_HTTP_PROTOCOL=http

# =====================================================
# Google Maps
# Separate keys are used for browser and server requests
# =====================================================
GOOGLE_MAPS_BROWSER_KEY=your_browser_maps_key_here
GOOGLE_MAPS_SERVER_KEY=your_server_maps_key_here

# =====================================================
# Stripe
# Used for checkout, payment processing, and webhook validation
# =====================================================
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxx

# =====================================================
# Email Configuration (Brevo SMTP)
# Used for receipts, confirmations, newsletters, and notifications
# =====================================================
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-brevo-smtp-user@smtp-brevo.com
EMAIL_HOST_PASSWORD=your-brevo-smtp-key

DEFAULT_FROM_EMAIL=Tucker & Dale's Home Services <no-reply@tuckeranddales.com>

# =====================================================
# Security / Redirects
# =====================================================
SECURE_SSL_REDIRECT=False


```

Notes:
- `GOOGLE_MAPS_BROWSER_KEY` is used for front-end map rendering and should be restricted by HTTP referrers.
- `GOOGLE_MAPS_SERVER_KEY` is used for backend routing/availability logic and should be restricted by API scope, not website referrers.
- `DJANGO_PRODUCTION=False` is shown here to match the current project setup. Update according to your deployment strategy.

- Copy-paste the whole block into your project root as .env

- Replace every placeholder (especially SECRET_KEY, DATABASE_URL, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD) with your real values

- Never commit this file to Git (make sure .env is in .gitignore)

- For Heroku: Add these as Config Vars in the Heroku dashboard (Settings → Config Vars) instead of using a .env file

- Local testing: Uncomment the console.EmailBackend line temporarily if you want emails printed to the terminal instead of actually sent

- witch domains: Just comment/uncomment the alternative Brevo block and restart the server

### 🔐 API Key Security

Google Maps integration uses two separate API keys:

- **Browser key** (`GOOGLE_MAPS_BROWSER_KEY`)
  - Restricted by HTTP referrers (Heroku + custom domain)
  - Used only for front-end map rendering (Maps JavaScript API)

- **Server key** (`GOOGLE_MAPS_SERVER_KEY`)
  - No referrer restriction (required for backend requests)
  - Restricted to specific APIs (Directions, Distance Matrix, Geocoding)
  - Used for scheduling availability and routing logic

Previously exposed development keys were revoked and replaced.
All active keys are securely managed via environment variables and are not stored in the repository.

[Back to Table of Contents](#table-of-contents)
---

## Testing & Validation

Testing was carried out throughout development to ensure the application works as expected, both for end-users and administrators.
Drag-and-drop booking interaction is supported for desktop users with mouse or trackpad input with developer tools turned off. On touch devices and in Chrome DevTools mobile emulation, drag-and-drop is not relied upon, and tap-based Add to Cart interactions are used instead.

### Manual Testing

**Navigation & Layout**
- Home page loads successfully with hero section and service categories → ✅
- Navbar links work correctly: **Home**, **Book a Service**, **My Bookings**, **Payment History**, **Login / Register** → ✅
- Responsive mobile-first design verified using Chrome DevTools (Galaxy S21, iPhone 14, iPad) → ✅
- All pages reachable via main navigation (no orphan pages) → ✅

**Booking Workflow**
- “Book a Service” workflow successfully filters available time slots → ✅
- Selecting a date and address displays correct available slots → ✅
- Multiple services can be added to cart → ✅
- Checkout page redirects to Stripe (test mode) → ✅
- Successful payment triggers confirmation page and creates PaymentHistory + Booking records → ✅
- Cancel button on Payment History page cancels service and issues refund → ✅
- Refund confirmation email sent to registered user → ✅

**User Accounts**
- User registration and login/logout validated via Django Allauth → ✅
- Password reset emails delivered using test backend → ✅
- Profile info (billing + service address) retained across checkouts → ✅
- Duplicate registration prevented for existing email → ✅

**Admin Features**
- Admin login accessible at `/admin/` → ✅
- CRUD operations confirmed for Employees, Bookings, Service Categories, and Time Slots → ✅
- Inline Employee Assignments view lists linked bookings → ✅
- Manager role (superuser) can view all bookings; staff accounts have read-only access → ✅
- Graceful error handling confirmed (invalid or cancelled bookings handled cleanly) → ✅

**Billing & Payments**
- Stripe Checkout session created per active cart → ✅
- PaymentHistory table displays correct amount, date, and status → ✅
- Refund transactions link to parent payment record and show negative value → ✅
- Email receipts sent for successful payments and refunds → ✅
- Invoice page itemizes bookings and totals accurately → ✅

**SEO & Performance**
- Meta tags added for description, keywords, author, Open Graph, and Twitter → ✅
- robots.txt and sitemap.xml included for search engine crawling → ✅
- Custom 404 page displays friendly redirect to Home → ✅
- Page load time under 2 seconds in local testing → ✅
- All text reviewed for authenticity (no placeholder/Lorem Ipsum) → ✅
- **Deployed to**: [Heroku App URL](https://tucker-and-dales.herokuapp.com)
- **Meta validation**: [W3C HTML Validator](https://validator.w3.org/)
- **SEO Check**: [SEO Analyzer](https://www.seobility.net/en/seocheck/)

<!-- | ID  | Feature             | Test Steps                                     | Expected Result                                         | Result |
| --- | ------------------- | ---------------------------------------------- | ------------------------------------------------------- | ------ |
| FT1 | Book service        | Select date → choose employee → checkout → pay | Booking created and visible in dashboard                | Pass   |
| FT2 | Cancel booking      | Cancel existing booking                        | Status changes to cancelled and moves to refund section | Pass   |
| FT3 | Rebook after cancel | Book same slot again and pay                   | New active booking created, old remains cancelled       | Pass   |
| FT4 | Payment history     | View history page                              | Payment linked correctly to bookings                    | Pass   |

[add screenshots]

| Test                      | Input                                           | Expected                                             | Result |
| ------------------------- | ----------------------------------------------- | ---------------------------------------------------- | ------ |
| Past-date booking blocked | Select a past service date and continue booking | validation prevents checkout and shows error message | Pass   |
| Empty address             | Submit form without address                     | Form blocked and validation message shown            | Pass   |
| Duplicate booking prevention| Attempt same slot twice                         | Prevented or handled correctly,  booking blocked                       | Pass   |
| Payment session mismatch  | Tampered `session_id`                           | Redirect with error message, no booking created      | Pass   |

| Test                         | Input                                                                                       | Expected                                                                       | Result |
| ---------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------ |
| Duplicate booking prevention | Attempt duplicate checkout for same employee/date/time slot via stale cart or repeated flow | Server-side validation blocks second booking creation and redirects with error | Pass   |

| Test                          | Input                                        | Expected                                                  | Result |
| ----------------------------- | -------------------------------------------- | --------------------------------------------------------- | ------ |
| Sold slot removed from search | Re-search same date after successful payment | Previously purchased employee/time slot no longer appears | Pass   |

| Test                           | Input                                                                 | Expected                                                  | Result |
| ------------------------------ | --------------------------------------------------------------------- | --------------------------------------------------------- | ------ |
| Sold slot removed from search  | Re-search same date after successful payment                          | Previously purchased employee/time slot no longer appears | Pass   |
| Duplicate booking prevention   | Attempt to rebook same employee/date/time slot through normal UI flow | User cannot reselect sold slot or proceed to checkout     | Pass   |
| Reuse completed Stripe session | Duplicate checkout tab after first payment succeeds                   | Stripe refuses reused/completed session                   | Pass   | -->

| Test                                          | Input                                                                                     | Expected                                                                    | Result |
| --------------------------------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------ |
| Past-date booking blocked                     | Attempt booking/payment for a past date                                                   | validation blocks invalid booking before completion                         | Pass   |
| Empty address                                 | Submit form without address                                                               | Form blocked and validation message shown                                   | Pass   |
| Duplicate item in same cart                   | Attempt to add same employee/date/time slot twice in one cart                             | System prevents duplicate cart item or keeps a single valid cart entry      | Pass   |
| Sold slot removed from search                 | Complete payment, then run a fresh search for the same date                               | Previously purchased employee/time slot no longer appears in search results | Pass   |
| Duplicate booking prevented in normal UI flow | After successful payment, try to rebook same employee/date/time slot through a new search | User cannot reselect sold slot or proceed to checkout for that sold slot    | Pass   |
| Reuse completed Stripe session                | Duplicate checkout tab and attempt payment again after first payment succeeds             | Stripe refuses reused/completed checkout session                            | Pass   |
| Payment session mismatch                      | Tampered `session_id`                                                                     | Redirect with error message, no invalid booking created                     | Pass   |


Past dates may be viewed for reference, but booking them is prevented through server-side validation at cart and checkout stages.
Tested booking flow with a past date. The application now correctly prevents the booking from proceeding to payment and displays a validation error, confirming invalid historical dates are blocked.

Testing identified a critical issue where the same employee time slot could be booked and paid for multiple times.

The root cause was that availability logic did not exclude already-booked employees for a given date and time slot.

This was resolved by updating the availability query so that employees with existing bookings are excluded from search results.

After the fix:

- booked slots no longer appear in search results
- users cannot re-add or rebook the same slot
- Stripe prevents reuse of completed checkout sessions

This ensures booking consistency and prevents duplicate payments in the normal user flow.

- After successful payment, booked employee/time slots are immediately excluded from subsequent searches for the same date. This prevents duplicate bookings through the normal user flow. Stripe also prevents reuse of completed checkout sessions.


- Authentication and access control are implemented using Django’s authentication system and django-allauth.

- Users must be logged in to access booking, cart, and checkout functionality. Unauthorized access attempts are redirected to the login page.

- User data is linked to bookings, ensuring that each booking is associated with a specific authenticated user.

[Back to Table of Contents](#table-of-contents)
---


## Testing & Validation

This section documents the final validation work completed on the application.
validation focused on standards compliance, code quality, and runtime correctness across HTML, CSS, JavaScript, and Python.

---

### Validation Summary

| Test ID | Area | Tool | Expected | Result |
|---|---|---|---|---|
| VT-05 | HTML validation | W3C Markup Validator | No critical errors in rendered templates | Pass |
| VT-06 | CSS validation | W3C CSS Validator | No blocking errors in custom stylesheets | Pass (warnings only) |
| VT-07 | JavaScript validation | JSHint | No syntax errors in custom scripts | Pass |
| VT-08 | Python validation | Flake8 | No critical syntax, import, or style errors in project code | Pass |

---
#### **VT-05 HTML Validation**

All key **user-facing templates** were validated using the W3C Markup validation Service.

#### **Scope**
validation was performed on the **rendered HTML output** of the application, rather than raw Django template files, because template inheritance and includes are only fully represented after rendering.

Validated pages included:

- Home page
- Login page
- Signup page
- Search by Date
- Search by Time Slot
- Checkout
- Complete Profile
- Payment History
- Live Invoice
- Password Change
- Password Reset
- Password Reset Done
- Confirm Email / Check Inbox
- Staff Dashboard
- Custom 404 page
- Custom 500 page

#### **Notes**
- Structural issues such as invalid nesting, duplicate declarations, missing required elements, and modal markup errors were corrected
- Accessibility issues such as ARIA misuse and heading hierarchy were reviewed and fixed where needed
- validation focused on the pages most relevant to the live user journey and project functionality

### Detailed validation Evidence

| Test ID | Area | File / Page | Tool | Expected | Result |
|---|---|---|---|---|---|
| VT-05.1 | HTML validation | `home` | W3C Markup Validator | No critical errors | Pass |
| VT-05.2 | HTML validation | `login` | W3C Markup Validator | No critical errors | Pass |
| VT-05.3 | HTML validation | `signup` | W3C Markup Validator | No critical errors | Pass |
| VT-05.4 | HTML validation | `search_by_date` | W3C Markup Validator | No critical errors | Pass |
| VT-05.5 | HTML validation | `search_by_time_slot` | W3C Markup Validator | No critical errors | Pass |
| VT-05.6 | HTML validation | `checkout` | W3C Markup Validator | No critical errors | Pass |
| VT-05.7 | HTML validation | `complete_profile` | W3C Markup Validator | No critical errors | Pass |
| VT-05.8 | HTML validation | `payment_history` | W3C Markup Validator | No critical errors | Pass |
| VT-05.9 | HTML validation | `live_invoice` | W3C Markup Validator | No critical errors | Pass |
| VT-05.10 | HTML validation | `password_change` | W3C Markup Validator | No critical errors | Pass |
| VT-05.11 | HTML validation | `password_reset` | W3C Markup Validator | No critical errors | Pass |
| VT-05.12 | HTML validation | `password_reset_done` | W3C Markup Validator | No critical errors | Pass |
| VT-05.13 | HTML validation | `confirm_email_check_inbox` | W3C Markup Validator | No critical errors | Pass |
| VT-05.14 | HTML validation | `staff_dashboard` | W3C Markup Validator | No critical errors | Pass |
| VT-05.15 | HTML validation | `error_404` | W3C Markup Validator | No critical errors | Pass |
| VT-05.16 | HTML validation | `error_500` | W3C Markup Validator | No critical errors | Pass |

### Evidence

- VT-05.1 ![HTML validation — Home](./images/testing_screenshots/validation/html/home.png)

- VT-05.2 ![HTML validation — Login](./images/testing_screenshots/validation/html/login.png)

- VT-05.3 ![HTML validation — Signup](./images/testing_screenshots/validation/html/signup.png)

- VT-05.4 ![HTML validation — Search by Date](./images/testing_screenshots/validation/html/search-by-date.png)

- VT-05.5 ![HTML validation — Search by Time Slot](./images/testing_screenshots/validation/html/search-by-timeslot.png)

- VT-05.6 ![HTML validation — Checkout](./images/testing_screenshots/validation/html/checkout.png)

- VT-05.7 ![HTML validation — Complete Profile](./images/testing_screenshots/validation/html/complete-profile.png)

- VT-05.8 ![HTML validation — Payment History](./images/testing_screenshots/validation/html/payment-history.png)

- VT-05.9 ![HTML validation — Live Invoice](./images/testing_screenshots/validation/html/live-invoice.png)

- VT-05.10 ![HTML validation — Password Change](./images/testing_screenshots/validation/html/password-change.png)

- VT-05.11 ![HTML validation — Password Reset](./images/testing_screenshots/validation/html/password-reset.png)

- VT-05.12 ![HTML validation — Password Reset Done](./images/testing_screenshots/validation/html/password-reset-done.png)

- VT-05.13 ![HTML validation — Confirm Email / Check Inbox](./images/testing_screenshots/validation/html/confirm-email-check-inbox.png)

- VT-05.14 ![HTML validation — Staff Dashboard](./images/testing_screenshots/validation/html/staff-dashboard.png)

- VT-05.15 ![HTML validation — 404 Page](./images/testing_screenshots/validation/html/error-404.png)

- VT-05.16 ![HTML validation — 500 Page](./images/testing_screenshots/validation/html/error-500.png)

---

#### **VT-06 CSS Validation**

Custom CSS was validated using the W3C CSS Validation Service.

#### **Notes**
- No blocking CSS errors were found
- Warnings were reviewed and accepted, including:
  - CSS variables (not statically analyzable)
  - vendor-specific pseudo-elements such as `::-webkit-scrollbar`
  - deprecated `break-word` usage
- These warnings do not impact functionality or rendering

### Evidence

- CSS Validation ![CSS Validation](./images/testing_screenshots/validation/html/css_validation.png)

---

[Back to Table of Contents](#table-of-contents)

#### **VT-07 JavaScript Validation**

Custom JavaScript was validated using JSHint.

#### **Notes**
- ES11 was enabled to support modern JavaScript syntax
- Required globals such as `google` were declared where needed
- Templates containing multiple `<script>` blocks were validated **one script at a time**
- No syntax errors remained after configuration and cleanup

---

#### 🔎 **Detailed Validation Results**

| Test ID | Area | File / Page | Tool | Expected | Result |
|---|---|---|---|---|---|
| VT-07.1.1 | JavaScript validation | `search_by_date.html` (map script) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.1.2 | JavaScript validation | `search_by_date.html` (cart script) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.2.1 | JavaScript validation | `search_by_time_slot.html` (map script) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.2.2 | JavaScript validation | `search_by_time_slot.html` (cart script) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.3.1 | JavaScript validation | `_cart.html` (cart script) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.4.1 | JavaScript validation | `checkout.html` (checkout script) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.5.1 | JavaScript validation | `live_invoice.html` | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.6.1 | JavaScript validation | `payment_history.html` | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.7.1 | JavaScript validation | `base_search.html` (script 1) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.7.2 | JavaScript validation | `base_search.html` (script 2) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.7.3 | JavaScript validation | `base_search.html` (script 3) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.8.1 | JavaScript validation | `base.html` (cart script) | JSHint | No syntax errors | Pass — no errors or warnings |
| VT-07.8.2 | JavaScript validation | `base.html` (drag/drop script) | JSHint | No syntax errors | Pass — no errors or warnings |

---

### Evidence

- VT-07.1.1 ![JSHint — Search by Date Map](./images/testing_screenshots/validation/js/search-by-date-maps.png)
- VT-07.1.2 ![JSHint — Search by Date Cart](./images/testing_screenshots/validation/js/search-by-date-cart.png)
- VT-07.2.1 ![JSHint — Search by Time Slot Map](./images/testing_screenshots/validation/js/search-by-timeslot-maps.png)
- VT-07.2.2 ![JSHint — Search by Time Slot Cart](./images/testing_screenshots/validation/js/search-by-timeslot-cart.png)
- VT-07.3.1 ![JSHint — Cart Partial](./images/testing_screenshots/validation/js/cart.png)
- VT-07.4.1 ![JSHint — Checkout](./images/testing_screenshots/validation/js/checkout.png)
- VT-07.5.1 ![JSHint — Live Invoice](./images/testing_screenshots/validation/js/live-invoice.png)
- VT-07.6.1 ![JSHint — Payment History](./images/testing_screenshots/validation/js/payment-history.png)
- VT-07.7.1 ![JSHint — Base Search Script 1](./images/testing_screenshots/validation/js/base-search-1.png)
- VT-07.7.2 ![JSHint — Base Search Script 2](./images/testing_screenshots/validation/js/base-search-2.png)
- VT-07.7.3 ![JSHint — Base Search Script 3](./images/testing_screenshots/validation/js/base-search-3.png)
- VT-07.8.1 ![JSHint — Base Script 1](./images/testing_screenshots/validation/js/base-1.png)
- VT-07.8.2 ![JSHint — Base Script 2](./images/testing_screenshots/validation/js/base-2.png)

---

### Summary

JavaScript validation confirmed that:

- all custom scripts were syntactically valid
- templates containing multiple script blocks were validated individually
- modern JavaScript features were configured correctly in JSHint
- dynamic features such as maps, cart updates, drag-and-drop, and checkout interactions were supported by clean validation results

This confirms that the project’s custom client-side logic is maintainable, standards-aware, and free from blocking syntax issues.

---

[Back to Table of Contents](#table-of-contents)

| Test ID | Area | File / Page | Tool | Expected | Result |
|---|---|---|---|---|---|
| VT-08.1 | Python validation | Project codebase | Flake8 | No critical Python syntax or style errors | Pass — no errors after fixes |

#### **VT-08 Python Validation**

Python code was validated using Flake8 to assess compliance with PEP 8 standards and to identify syntax or logical issues.

Validation was executed using the following command:

    flake8 core customers billing scheduling tucker_and_dales_home_services --exclude=migrations

The validation focused on project-specific application code. Automatically generated files such as migrations were excluded.
Minor stylistic decisions such as line wrapping were handled using standard Python formatting practices (parentheses-based line continuation)
to preserve readability without altering functionality.


#### **Results**

- No syntax errors (E999) were present after corrections
- No undefined names (F821) or import issues (F401, F811) remained
- Code structure and formatting were aligned with PEP 8 guidelines
- Line-length issues (E501) were reviewed and resolved where necessary to maintain readability and consistency

All identified issues were addressed, resulting in a clean Flake8 report with no remaining errors.

#### **Evidence**

-  VT-08.1

 ![PEP 8](./images/testing_screenshots/validation/python/pep8._results.png)

---
[Back to Table of Contents](#table-of-contents)

#### **Browser & Responsiveness Testing**

The application was tested across multiple screen sizes to ensure responsive behavior, usability, and layout stability under real-world conditions.

#### **Scope**

Testing covered:

- mobile devices (≈412px width)
- tablet devices (≈768px width)
- desktop screens (≥1200px width)

Focus areas included:

- navigation usability
- layout responsiveness
- readability of content
- table and grid behavior
- modal rendering (map and checkout)
- checkout and payment flows

---

#### **Detailed Results**

| Test ID | Scenario | Expected Behavior | Result |
|---|---|---|---|
| VT-11.1 | Home page (mobile) | Layout adapts and remains readable | Pass |
| VT-11.2 | Search flow (mobile) | User can initiate and complete search | Pass |
| VT-11.3 | Search results (mobile) | Results display clearly without layout breakage | Pass |
| VT-11.4 | Map modal (mobile) | Map renders correctly within modal | Pass |
| VT-11.5 | Checkout summary (mobile) | Tables and totals remain readable | Pass |
| VT-11.6 | Payment history (mobile) | Data displayed correctly after checkout | Pass |
| VT-11.7 | Stripe checkout (mobile) | External checkout flow renders correctly | Pass |
| VT-11.8 | Live invoice (mobile) | Invoice layout remains usable and readable | Pass |

---

#### **Evidence**

- VT-11.1

![Mobile — Home Page](./images/testing_screenshots/Mobile_responsiveness/01-Home-page.PNG)

- VT-11.2

![Mobile — Begin Search](./images/testing_screenshots/Mobile_responsiveness/02-Begin-search.PNG)

- VT-11.3

![Mobile — Search Results](./images/testing_screenshots/Mobile_responsiveness/03-Search-results.PNG)

- VT-11.4

![Mobile — View Routes](./images/testing_screenshots/Mobile_responsiveness/04-View-routes.PNG)

---
- VT-11.5

![Mobile — Checkout Summary (Before Fix)](./images/testing_screenshots/Mobile_responsiveness/05a-Checkout-summary-before-tables-squahed.png)

 ![Mobile — Checkout Summary](./images/testing_screenshots/Mobile_responsiveness/05b-Checkout-summary.PNG)

---
- VT-11.6

![Mobile — Payment History](./images/testing_screenshots/Mobile_responsiveness/06-Checkout-success-Payment-History.PNG)

- VT-11.7

![Mobile — Stripe Checkout](./images/testing_screenshots/Mobile_responsiveness/07-Stripe-checkout.PNG)

- VT-11.8

![Mobile — Live Invoice](./images/testing_screenshots/Mobile_responsiveness/08-Live-invoice-used-for-adjustments.PNG)

---

#### **Summary**

Responsive testing confirmed that:

- layouts adapt correctly across screen sizes
- navigation remains usable on mobile devices
- booking and checkout flows function without UI breakage
- tables and data-heavy views remain readable after layout adjustments
- modal components (including maps) render correctly on smaller screens

These results demonstrate that the application provides a consistent and usable experience across devices.

---

[Back to Table of Contents](#table-of-contents)

## Defensive Programming Strategy

### Defensive Programming & Edge Case Testing

The system was tested against invalid inputs, edge cases, and concurrency scenarios to ensure robustness, data integrity, and safe failure handling.

This section focuses on **preventing incorrect system states**, rather than standard successful workflows.

---

### Scope

Testing covered:

- invalid user input handling
- booking constraints (past dates, missing data)
- availability protection
- duplicate booking prevention
- concurrent checkout scenarios
- payment failure handling

---

#### **Detailed Results**

| Test ID | Scenario | Expected Behavior | Result |
|---|---|---|---|
| VT-12.1 | Past date search | System allows search but prevents booking | Pass |
| VT-12.2 | Past date booking attempt | Booking is blocked | Pass |
| VT-12.3 | Missing address input | Validation error prevents search | Pass |
| VT-12.4 | Timeslot availability before booking | Slot shown as available | Pass |
| VT-12.5 | Timeslot added to cart | Slot reserved temporarily | Pass |
| VT-12.6 | Timeslot after payment | Slot no longer available | Pass |
| VT-12.7 | Duplicate booking attempt | System prevents double booking | Pass |
| VT-12.8 | Concurrent checkout (multi-tab) | Duplicate transaction blocked | Pass |
| VT-12.9 | Payment failure | User returned safely to checkout | Pass |

---

#### **Evidence**

#### Input Validation

- VT-12.1 ![Past Date Search](./images/testing_screenshots/PASS_4/booking_lifecycle/18-past-date-search.png)

- VT-12.2 ![Past Date Booking Denied](./images/testing_screenshots/PASS_4/booking_lifecycle/19-past-date-booking-denied.png)

- VT-12.3 ![Empty Address Denied](./images/testing_screenshots/PASS_4/booking_lifecycle/20-empty-address-search-denied.png)

---

#### Availability & Data Integrity

- VT-12.4 ![Timeslot Available Before Payment](./images/testing_screenshots/PASS_4/booking_lifecycle/21-timeslot-available-before-payment.png)

- VT-12.5 ![Timeslot in Cart](./images/testing_screenshots/PASS_4/booking_lifecycle/22-timeslot-in-cart.png)

- VT-12.6 ![Timeslot Payment](./images/testing_screenshots/PASS_4/booking_lifecycle/23-payment-for-timeslot.png)

![Timeslot in Payment History](./images/testing_screenshots/PASS_4/booking_lifecycle/24-timeslot-in-payment-history.png)

![Timeslot in Admin Payment History](./images/testing_screenshots/PASS_4/booking_lifecycle/25-timeslot-in-admin-payment-history.png)

![Timeslot in Admin Bookings](./images/testing_screenshots/PASS_4/booking_lifecycle/26-timeslot-in-admin-bookings.png)

---

#### Duplicate Booking Prevention

- VT-12.7 ![Duplicate Timeslot Blocked](./images/testing_screenshots/PASS_4/booking_lifecycle/27-search-same-timeslot-on-same-day-after-booking.png)

---

#### Concurrent Checkout Protection

- VT-12.8 ![Checkout Summary](./images/testing_screenshots/PASS_4/booking_lifecycle/28-checkout-summary.png)

![Checkout Tab A](./images/testing_screenshots/PASS_4/booking_lifecycle/29-checkout-on-tab-A.png)


![Duplicate Checkout Created](./images/testing_screenshots/PASS_4/booking_lifecycle/30-create-duplicate-checkout-tab-B.png)

![Checkout Success Tab A](./images/testing_screenshots/PASS_4/booking_lifecycle/31-checkout-success-tab-A.png)

- VT-12.9 ![Duplicate Checkout Attempted](./images/testing_screenshots/PASS_4/booking_lifecycle/32a-attempt-checkout-on-duplicate-tab-B.png)

![Duplicate Checkout Blocked](./images/testing_screenshots/PASS_4/booking_lifecycle/32b-checkout-on-duplicate-tab-B-blocked.png)

---

#### Payment Failure Handling (Stripe and Admin)

- Declined Payment — Return to Checkout

![Declined Payment — Return to Checkout](./images/testing_screenshots//Stripe/01-Card-declined.png)

- Terminal result - Declined Attempt - No Email Sent (verified via heroku logs --tail -a tucker-and-dales-home-services)

![Terminal result](./images/testing_screenshots//Stripe/02-Payment-fail.png)

- Declined Attempt — verified via Stripe dashboard

![Declined Attempt](./images/testing_screenshots//Stripe/03-Stripe-failure-confirmation.png)


- Declined Attempt — verified via Admin payment history

![Declined Attempt](./images/testing_screenshots//Stripe/04-Admin_confirmation.png)

- Declined Attempt — verified via Admin bookings

![Declined Attempt](./images/testing_screenshots//Stripe/05-Admin-confirmation-bookings.png)

- Back to cart — checkout summary intact

![Declined Attempt](./images/testing_screenshots//Stripe/06-Back-to-checkout-summary.png)

---

#### **Summary**

Defensive testing confirmed that:

- invalid inputs are correctly rejected before processing
- bookings cannot be created for past dates or incomplete data
- timeslot availability is consistently enforced across cart and payment states
- duplicate bookings are prevented at both search and checkout stages
- concurrent checkout attempts are safely handled without creating duplicate transactions
- failed payments do not result in inconsistent or partial booking states

These controls ensure that the system remains reliable and maintains data integrity under adverse conditions.

---

[Back to Table of Contents](#table-of-contents)

<!-- ## 🔄 Booking Lifecycle Testing

[UNCHANGED — full evidence section]

---

### 🧠 Summary

The system demonstrates:

* full lifecycle integrity
* strong validation controls
* prevention of race conditions
* reliable payment handling -->

---

## User Stories

User stories are tracked in a GitHub Project:

👉 View full project board and user stories here:
👉 [User Stories Board](https://github.com/users/Pacman0126/projects/7/)

### 🧩 Agile Planning & Project Management

User stories were documented and managed using GitHub Issues and Project Boards, with acceptance criteria and MoSCoW prioritisation.

User stories were tested manually to confirm that implemented functionality meets user requirements.

Full user stories, including descriptions, acceptance criteria, and prioritisation (MoSCoW), are maintained in GitHub Issues and Project Boards.

Each user story includes:
- a clear description
- acceptance criteria
- MoSCoW prioritisation

To improve project organisation, user stories were grouped into higher-level themes (epics), including:

- Authentication & User Management
- Service Search & Booking
- Checkout & Payments
- Admin & Data Management


This structure supports clear prioritisation, progress tracking, and alignment with project goals.

---
### 🎨 Design Considerations

The application uses a consistent visual approach with a focus on readability, clear hierarchy, and usability. Styling choices were guided by practical UI considerations, including contrast, spacing, and responsive layout behaviour.

---

[Back to Table of Contents](#table-of-contents)

## User Story Results

### 🧪 User Story Testing

| ID | User Story | Result | Evidence |
|---|---|---|---|
| US-01 | As a new user, I want to register an account, so that I can access booking and payment features. | Pass | VT-10A |
| US-02 | As a registered user, I want to receive account-related email confirmation, so that I can verify successful registration. | Pass | VT-10A |
| US-03 | As a registered user, I want to log in securely, so that I can access protected account features. | Pass | VT-10A |
| US-04 | As a logged-in user, I want to log out securely, so that I can end my session safely. | Pass | VT-10A |
| US-05 | As a logged-in user, I want to update my profile information, so that my account details stay accurate. | Pass | VT-10A |
| US-06 | As an authenticated user, I want protected pages to require login, so that my account data remains secure. | Pass | VT-10A |
| US-07 | As a customer, I want to search for services by date, so that I can find available appointments on a specific day. | Pass | VT-10B |
| US-08 | As a customer, I want to search for services by time slot, so that I can book work around my schedule. | Pass | VT-10B |
| US-09 | As a customer, I want to view available employees and services, so that I can choose a suitable booking. | Pass | VT-10B |
| US-10 | As a customer, I want to view routes on a map, so that I can understand employee travel coverage. | Pass | VT-10B |
| US-11 | As a customer, I want to add a selected service to my cart, so that I can review it before payment. | Pass | VT-10B |
| US-12 | As a customer, I want the cart to update dynamically, so that I can see current selections and totals immediately. | Pass | VT-10B |
| US-13 | As a customer, I want to review my cart summary, so that I can confirm the selected booking details before checkout. | Pass | VT-10B |
| US-14 | As a customer, I want to remove draft items from my cart, so that I can change my mind before payment. | Pass | VT-10B / CRUD |
| US-15 | As a customer, I want to proceed to checkout, so that I can complete payment for my selected services. | Pass | VT-10B |
| US-16 | As a customer, I want checkout totals to be accurate, so that I know exactly what I will be charged. | Pass | VT-10B |
| US-17 | As a customer, I want to complete payment securely, so that my booking is confirmed. | Pass | VT-10B / PASS 4 |
| US-18 | As a customer, I want successful payment feedback, so that I know my purchase has completed. | Pass | VT-10B / PASS 4 |
| US-19 | As a customer, I want my booking to appear in payment history, so that I can track my services. | Pass | VT-10B / PASS 4 |
| US-20 | As a customer, I want an invoice to be generated, so that I have a record of the transaction. | Pass | VT-10B / PASS 4 |
| US-21 | As a customer, I want cancellation and refund records to be reflected correctly, so that my payment history remains accurate. | Pass | PASS 4 |
| US-22 | As an admin, I want to view bookings, so that I can manage operational activity. | Pass | PASS 4 |
| US-23 | As an admin, I want to view payments, so that I can verify completed and adjusted transactions. | Pass | PASS 4 |
| US-24 | As a customer, I want past-date bookings to be blocked, so that invalid bookings cannot be created. | Pass | VT-12 |
| US-25 | As a customer, I want missing required inputs to be rejected, so that incomplete requests are not processed. | Pass | VT-12 |
| US-26 | As a customer, I want timeslot availability to update correctly, so that already-selected or completed bookings cannot be duplicated. | Pass | VT-12 |
| US-27 | As a customer, I want duplicate bookings to be prevented, so that the same slot cannot be booked twice. | Pass | VT-12 |
| US-28 | As a customer, I want concurrent checkout attempts to be handled safely, so that duplicate payments are blocked. | Pass | VT-12 |
| US-29 | As a customer, I want failed payments to return safely to checkout, so that my session remains recoverable. | Pass | VT-12 |
| US-30 | As a user, I want the system to preserve data integrity across booking, payment, and admin views, so that records remain consistent throughout the lifecycle. | Pass | PASS 4 / VT-12 |


---

#### **Summary**

All defined user stories were implemented and tested successfully.

Each story is supported by:
- functional testing (VT-10A / VT-10B)
- defensive testing (VT-12)
- lifecycle validation (PASS 4)

This confirms full alignment between planned features and implemented functionality

[Back to Table of Contents](#table-of-contents)
---

## SEO & Discoverability

Search Engine Optimisation (SEO) was implemented to improve visibility, accessibility, and discoverability of the application, while maintaining a clean and user-focused experience.

---

### 🌐 Domain & Deployment

- Custom domain configured: **https://www.tuckeranddales.com**
- HTTPS enabled via SSL certificate (automatic certificate management)
- Canonical domain used consistently across:
  - Meta tags
  - Sitemap
  - Application routing
- Redirect strategy ensures consistent domain usage (`www` preferred)

---

### 🧠 Meta Tags & Social Sharing

Core SEO meta tags are implemented in the base template to ensure consistent coverage across the application:

- `description` (default + page-specific overrides)
- `keywords`
- `author`
- `robots` (index, follow)
- Open Graph (`og:title`, `og:description`, `og:type`, `og:url`)
- Twitter Card metadata

Search-specific pages override the default meta description to reflect user intent (e.g. searching by date or time slot).

This ensures:
- Meaningful search snippets
- Improved click-through rates
- Better semantic relevance

---

### 🧭 Sitemap

A dynamic XML sitemap is provided at: /sitemap.xml

Includes:
- Core public-facing pages
- Booking/search entry points
- Authentication pages where appropriate

All URLs are generated using the production domain: https://www.tuckeranddales.com/


This supports:
- Efficient search engine indexing
- Accurate crawling of live routes

---

### 🤖 Robots.txt

A `robots.txt` file is implemented at: /robots.txt


Key directives:

- Allows indexing of public pages
- Blocks administrative routes (`/admin/`)
- References sitemap location

Example:

User-agent: *
Disallow: /admin/
Sitemap: https://www.tuckeranddales.com/sitemap.xml


---

### 🧱 Template Architecture (SEO-Aware)

SEO is integrated at the template level:

- `base.html` defines global meta structure
- `{% block meta_description %}` enables page-level overrides
- `base_search.html` provides contextual SEO for search workflows

This ensures:
- DRY implementation
- Consistent metadata across pages
- Flexibility for future expansion

---

### ⚡ Performance & UX Considerations

- Responsive design (mobile-first approach)
- Optimised asset loading via CDN (Bootstrap, Icons)
- Clean semantic HTML structure
- Fast load times via Heroku deployment

These factors contribute indirectly to SEO through:
- Improved user engagement
- Reduced bounce rates
- Better search ranking signals

---

### 📌 SEO Strategy Rationale

The SEO approach focuses on:

- **User intent** (search-driven booking flows)
- **Clarity over keyword stuffing**
- **Technical correctness** (sitemap, robots, HTTPS)
- **Maintainability** via template inheritance

Given the nature of the application (authenticated booking system), SEO efforts are intentionally concentrated on:

- Entry points (home page)
- Search interfaces
- Public-facing content

---

### 📸 Evidence

- Sitemap XML
![Sitemap XML](./images/testing_screenshots/SEO/sitemap-xml.png)

- Robots.txt
![Robots.txt](./images/testing_screenshots/SEO/robots-txt.png)

- Home page
![Home page](./images/testing_screenshots/SEO/base-meta-descriptions.png)

- Search page
![Search page](./images/testing_screenshots/SEO/base-search-meta-descriptions.png)

- Custom 404 Page
![Custom 404 Page](./images/testing_screenshots/SEO/error-custom-404.png)

---

[Back to Table of Contents](#table-of-contents)


## Marketing & Business Model

---

## 🔹 Marketing Strategy

### Facebook Business Page Mockup

As part of the marketing strategy, a **Facebook Business Page mockup** was created to simulate brand presence and audience engagement.

The mockup demonstrates:

* a clearly defined service offering (lawn care, house cleaning, garage and basement services)
* targeting of both **individual homeowners** and **multi-property users** such as landlords and property managers
* a structured content strategy including promotional posts, feature highlights, and customer testimonials
* clear call-to-action elements directing users to book services through the platform

The purpose of this approach is to:

* increase brand awareness
* communicate the value of the application
* drive user engagement and bookings

Rather than deploying a live page, a **high-fidelity visual mockup** was created using Figma to represent how the business would appear on Facebook.

### Mockup Evidence

![Facebook Mockup](./images/tuckers-mockup-facebook-business-page.png)

---

### Newsletter Integration

A newsletter subscription system is implemented to support ongoing user engagement and retention.

* Users receive confirmation upon subscription
* Email communication is handled via transactional email integration
* This supports future marketing campaigns such as promotions, reminders, and service updates

---

## E-Commerce Business Model

### Overview

This application operates as a **service-based e-commerce platform**, allowing users to book home services online with integrated payment processing.

The platform provides a streamlined booking experience for:

* **Homeowners** needing one-off services
* **Landlords and property managers** managing multiple properties

The business philosophy of this application is that once a customer books and pays for a time slot, it becomes their owned reservation.

Only the customer and the superuser (admin) are permitted to cancel, update, or delete paid bookings. Upon successful payment, the booking is finalized and the assigned employee’s schedule is updated accordingly.

This approach enforces clear ownership and prevents conflicting changes by multiple staff members, ensuring consistency in scheduling and maintaining a reliable customer experience.

This design supports accountability, auditability, and customer trust in the booking system.
---

### Value Proposition

The system delivers value through:

* **Convenience**: Users can book services in minutes without manual coordination
* **Transparency**: Clear pricing and structured service selection
* **Efficiency**: Assigned service professionals and scheduled time slots
* **Centralisation**: Booking history and service tracking in one platform

---

### Revenue Model

Revenue is generated through:

* **Per-service payments** processed at checkout
* Each booking represents a completed transaction
* Payments are handled securely via Stripe integration

This follows a **transaction-based revenue model**, typical of service marketplaces.

---

### Booking & Payment Flow

1. User selects a service (lawn care, cleaning, garage/basement service)
2. User chooses date and time slot
3. Service is added to cart
4. User completes checkout via Stripe
5. Payment is recorded
6. Booking is created and linked to the payment

This ensures:

* no invalid bookings without payment
* consistent transaction tracking
* reliable service scheduling

---

### Target Market

The platform is designed for two primary user groups:

* **Individual residential customers**

  * booking services for their own homes

* **Multi-property users** (landlords / property managers)

  * managing maintenance across multiple locations

This dual-target approach increases usability and market reach.

---

### Business Viability

The model is scalable due to:

* repeat service demand (cleaning, lawn care, maintenance)
* potential for subscription or recurring services
* expansion into additional service categories

The application demonstrates a realistic and commercially viable approach to delivering and monetising home services online.

[Back to Table of Contents](#table-of-contents)

# Tucker Resubmit Pass Blockers

## 🎯 Final Notes / Assessor Checklist

## Auth
- [ ] Register works
- [ ] Email verification works
- [ ] Login works
- [ ] Logout works
- [ ] My Profile works
- [ ] Restricted pages block anonymous users
- [ ] Role restrictions verified

## CRUD / Forms
- [ ] Create form with validation
- [ ] Edit form with validation
- [ ] validation errors visible
- [ ] CRUD reachable from UI
- [ ] Employee detail click-through works

## E-commerce
- [ ] Service/booking selection works
- [ ] Cart or equivalent works
- [ ] Checkout works
- [ ] Payment success feedback works
- [ ] Payment failure/cancel feedback works
- [ ] Booking/order saved
- [ ] Confirmation email sent

## Stability
- [ ] My Profile no longer 500s
- [ ] Logout no longer 500s
- [ ] Map page works or is removed from claims/UI
- [ ] No dead internal links

## SEO
- [ ] Meta descriptions present
- [ ] robots.txt present
- [ ] sitemap.xml present
- [ ] 404 page present
- [ ] Pages reachable by internal links

## Marketing / Docs
- [ ] Newsletter form visible on UI
- [ ] Facebook page or mockup ready
- [ ] E-commerce business model added to README
- [ ] README matches deployed behavior

## Credits
hero.png from https://www.moviepilot.de/movies/tucker-dale-vs-evil/bilder/374767

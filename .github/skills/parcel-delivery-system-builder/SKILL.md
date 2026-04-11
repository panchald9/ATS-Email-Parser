---
name: parcel-delivery-system-builder
description: 'Design and scaffold a production-ready Parcel Delivery Management System using React frontend, Node.js Express backend, PostgreSQL/MySQL database, and Python AI services. Use for full-stack architecture, JWT auth, parcel booking, tracking, admin dashboards, payments, ML prediction, route optimization, deployment planning, and setup documentation.'
argument-hint: 'Describe business constraints, preferred database, and whether to include Docker and payment gateway.'
user-invocable: true
---

# Parcel Delivery System Builder

## What This Skill Produces
- A complete implementation blueprint for a production-ready Parcel Delivery Management System.
- A text architecture diagram spanning frontend, backend, database, and Python AI service.
- A folder structure for all services with modular boundaries.
- Backend API design with auth, validation, error handling, logging, and sample requests.
- Frontend structure with state management, responsive dashboard UI, and charts.
- Database schema guidance for Users, Parcels, Orders, Tracking, Payments with indexing and normalization.
- AI module workflow for delivery-time prediction and optional optimization/anomaly features.
- Local setup instructions, environment configuration, deployment guidance, and scaling recommendations.

## When To Use
Use this skill when the user asks to:
- Build a complete logistics or parcel delivery app from scratch.
- Combine React + Node/Express + SQL + Python ML in one product.
- Get architecture, scaffolding, code samples, and setup docs in one pass.
- Add ML-assisted operational intelligence (prediction, routing, forecasting).

## Required Inputs
Collect or infer these before implementation:
- Target database: PostgreSQL or MySQL.
- Auth model: email/password, OAuth, or hybrid.
- Tracking model: polling, websocket, or event stream.
- Payment mode: mock or provider integration.
- AI scope: prediction only, or include route optimization and anomaly detection.
- Deployment target: local only, VM, container platform, or managed cloud.

## Procedure
1. Confirm delivery scope and constraints.
2. Propose architecture and service boundaries.
3. Define database schema, relationships, and indexes.
4. Scaffold backend modules and core middleware.
5. Implement auth and role-based access.
6. Implement parcel booking, order lifecycle, and tracking events.
7. Add admin analytics endpoints and report surfaces.
8. Scaffold frontend routes, state layer, API client, and dashboards.
9. Build Python ML service and inference API.
10. Integrate Node backend with AI service and fallback logic.
11. Add observability, config hygiene, and production hardening.
12. Provide setup, run, and deployment instructions.
13. Validate against completion criteria and known edge cases.

## Decision Points And Branching
- Database branch:
  - PostgreSQL: prefer JSONB for flexible event payloads and advanced indexing.
  - MySQL: prefer normalized tables and generated columns where needed.
- Tracking branch:
  - Real-time required: add websocket or server-sent events for status streaming.
  - Near real-time acceptable: use polling endpoints with incremental cursors.
- Payment branch:
  - Mock requested: implement deterministic fake provider with webhook simulator.
  - Real provider requested: add provider adapter, signature validation, idempotency keys.
- AI branch:
  - Minimal ML: delivery-time prediction only with batch retraining hooks.
  - Extended ML: add route optimization and demand forecasting pipelines.
- Deployment branch:
  - Docker requested: provide multi-service compose and health checks.
  - Non-Docker: provide native run scripts and env templates.

## Backend Standards
- Follow modular or MVC structure with clear service boundaries.
- Enforce JWT middleware and role checks for protected routes.
- Validate input at API boundary and return consistent error envelopes.
- Use structured logging with request correlation IDs.
- Add pagination, filtering, and sorting for list endpoints.
- Use transactions for multi-step order and payment workflows.

## Frontend Standards
- Use component-driven structure with reusable UI primitives.
- Use Redux Toolkit or Context API with explicit async state handling.
- Keep API client isolated and typed where possible.
- Build responsive dashboards with clear status visualizations and charts.
- Handle loading, empty, error, and retry states for every data view.

## AI Module Standards
- Start with a baseline regression model for delivery time prediction.
- Define minimal feature set: origin, destination, distance, parcel type, weather/time features.
- Expose inference and health endpoints via Flask or FastAPI.
- Version the model artifact and provide retraining workflow notes.
- Add graceful fallback in Node when AI service is unavailable.

## Completion Checks
A response is complete only if it includes:
- Text-based architecture diagram.
- Full folder structure for frontend, backend, AI service.
- Sample code snippets for each layer.
- Step-by-step local setup guide including env variables.
- Example REST endpoints and sample request/response payloads.
- Deployment guidance and scaling suggestions.
- Explicit assumptions and open risks.

## Quality Gates
- Security: password hashing, JWT expiry/refresh strategy, rate limiting.
- Reliability: idempotent status updates and payment callbacks.
- Data integrity: foreign keys, unique constraints, transactional consistency.
- Observability: logs, error boundaries, health checks, and metrics hooks.
- Maintainability: modular files, naming consistency, and concise comments.

## Output Format Template
Use this order in final output:
1. System architecture diagram (text).
2. Folder structure.
3. Database schema and index notes.
4. API design and sample endpoints.
5. Frontend approach and key components.
6. Python AI service design and sample model/inference code.
7. Integration flow between backend and AI.
8. Local setup and run steps.
9. Deployment strategy.
10. Scaling recommendations.
11. Assumptions, risks, and next actions.

## Prompt Starters
- Build a production Parcel Delivery Management System with React, Express, PostgreSQL, and FastAPI ML service.
- Generate an end-to-end architecture and starter code for parcel booking, tracking, admin analytics, and prediction.
- Scaffold backend APIs, frontend dashboard, and AI inference integration for logistics operations.

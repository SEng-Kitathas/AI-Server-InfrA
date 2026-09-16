# Receiver Ingress and Evaluation SOP

## Purpose
Forensic ingress, extraction, static inspection, compile verification, and package evaluation for PCMMAD receiver archive drops.

## Operating rule
The archive is copied into `incoming/`, extracted into `extracted/`, inventoried into `reports/`, and evaluated before any code is promoted.

## Promotion boundary
Extracted package files SHALL NOT be treated as promoted runtime code until explicitly copied into a controlled runtime or package surface after evaluation.

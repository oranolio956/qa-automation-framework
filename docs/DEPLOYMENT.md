# Deployment Guide

This repo is platform-agnostic. Use Dockerfiles and docker-compose for local testing. For cloud deployment, pick one option below and follow its provider docs:

- AWS ECS/Fargate: build and push images; define services and ALB; wire secrets (SSM/Secrets Manager)
- GCP Cloud Run: deploy each service image; set environment; add VPC connector if needed
- Kubernetes: create Deployments/Services/Ingress; optional Kong using `kong/kong.yml` as a reference

Environment variables are documented in `.env.example`. Do not commit secrets.
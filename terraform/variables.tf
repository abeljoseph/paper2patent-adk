variable "project_id" {
  description = "Google Cloud Project ID where services will be deployed."
  type        = string
}

variable "region" {
  description = "Google Cloud Region for deployment."
  type        = string
  default     = "us-central1"
}

variable "model_name" {
  description = "Default Gemini model name for the agent system."
  type        = string
  default     = "gemini-2.5-flash"
}

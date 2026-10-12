variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_owner" {
  description = "GitHub user or org that owns the repo, e.g. dansc0de"
  type        = string
}

variable "github_repo" {
  description = "Repository name without the owner, e.g. cloud-computing-fall-2026"
  type        = string
}

variable "github_owner_id" {
  description = "Numeric owner ID (./repo-ids.sh prints it). Only used with the immutable subject."
  type        = string
  default     = ""
}

variable "github_repo_id" {
  description = "Numeric repository ID (./repo-ids.sh prints it). Only used with the immutable subject."
  type        = string
  default     = ""
}

variable "use_immutable_subject" {
  description = "true for repos created after July 15, 2026 or opted in; false for older repos."
  type        = bool
  default     = true
}

variable "branch" {
  type    = string
  default = "main"
}

variable "create_oidc_provider" {
  description = "Set false if the account already has the GitHub OIDC provider."
  type        = bool
  default     = true
}

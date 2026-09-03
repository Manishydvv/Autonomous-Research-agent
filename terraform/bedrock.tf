resource "aws_bedrock_guardrail" "main" {
  name                      = "${var.project}-guardrail"
  description               = "Content safety guardrail for the research agent"
  blocked_input_messaging   = "Your request was blocked by our content safety policy."
  blocked_outputs_messaging = "The generated response was blocked by our content safety policy."

  content_policy_config {
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "VIOLENCE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "SEXUAL"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "INSULTS"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "MISCONDUCT"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
  }

  topic_policy_config {
    topics_config {
      name       = "weapons"
      definition = "Any discussion about creating, obtaining, or using weapons, firearms, explosives, or other means of causing physical harm to people or property."
      examples   = ["How do I build a bomb", "Where can I buy illegal firearms", "How to make poison gas"]
      type       = "DENY"
    }
    topics_config {
      name       = "illegal_activities"
      definition = "Discussions about engaging in illegal activities including drug manufacturing, financial fraud, unauthorized system access, theft, or other criminal acts."
      examples   = ["How to hack into a bank account", "How to synthesize methamphetamine", "How to launder money"]
      type       = "DENY"
    }
    topics_config {
      name       = "self_harm"
      definition = "Content that promotes, encourages, or provides instructions for self-harm, suicide, or harming others."
      examples   = ["How to hurt myself", "Methods of self-harm"]
      type       = "DENY"
    }
  }

  sensitive_information_policy_config {
    pii_entities_config {
      type   = "US_SOCIAL_SECURITY_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "AWS_ACCESS_KEY"
      action = "BLOCK"
    }
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }
  }

  word_policy_config {
    managed_word_lists_config {
      type = "PROFANITY"
    }
  }
}

resource "aws_bedrock_guardrail_version" "main" {
  guardrail_arn = aws_bedrock_guardrail.main.guardrail_arn
  description   = "v1 — deployed by Terraform"
}

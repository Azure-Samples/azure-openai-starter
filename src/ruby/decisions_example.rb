# frozen_string_literal: true

require "json"
require "open3"
require "openai"

# Ruby has no Azure Identity library, so ask the Azure Developer CLI for a token. This uses your
# `azd auth login` session, and the resource's tenant when AZURE_TENANT_ID is set.
def azd_token
  command = ["azd", "auth", "token", "--scope", "https://cognitiveservices.azure.com/.default", "--output", "json"]
  tenant = ENV["AZURE_TENANT_ID"]
  command += ["--tenant-id", tenant] if tenant && !tenant.empty?
  stdout, _stderr, status = Open3.capture3(*command)
  raise "azd auth token failed. Run `azd auth login` and try again." unless status.success?

  JSON.parse(stdout).fetch("token")
end

endpoint = ENV.fetch("AZURE_OPENAI_ENDPOINT")
# This is your Azure deployment name; the deployment must host gpt-6-luna.
model = ENV.fetch("AZURE_OPENAI_DEPLOYMENT", "gpt-6-luna")

# Entra ID is the default. Set AZURE_OPENAI_API_KEY only for the key fallback.
api_key = ENV["AZURE_OPENAI_API_KEY"]
api_key = azd_token if api_key.nil? || api_key.empty?

client = OpenAI::Client.new(
  api_key: api_key,
  base_url: "#{endpoint.sub(%r{/+\z}, "")}/openai/v1/"
)

begin
  # Batch related questions in one request.
  # [START decisions_request]
  decision = client.decisions.create(
    model: model,
    input: "I was charged twice for order 123. Please refund the duplicate charge.",
    questions: [
      {
        type: "predicate",
        name: "refund_requested",
        instructions: "Does the customer request a refund?"
      },
      {
        type: "choice",
        name: "department",
        instructions: "Which department should handle this request?",
        choices: [
          {value: "billing", description: "Payments and refunds."},
          {value: "technical", description: "Product problems."},
          {value: "other", description: "Other requests."}
        ]
      },
      {
        type: "score",
        name: "severity",
        instructions: "How severe is this issue?",
        levels: [
          {label: "Low", description: "Minor inconvenience."},
          {label: "Medium", description: "Needs attention."},
          {label: "High", description: "Urgent action needed."}
        ]
      }
    ]
  )
  # [END decisions_request]
rescue OpenAI::Errors::APIStatusError => error
  # The SDK's error message leaves out the service's message, so add the response body.
  abort "#{error.message}: #{error.body.inspect}"
end

raise "Decisions response is missing answers or usage" unless decision.answers&.any? && decision.usage

decision.answers.each do |answer|
  case answer
  when OpenAI::Models::Decision::Answer::Predicate
    puts "#{answer.name} (predicate): probability=#{answer.probability}"
  when OpenAI::Models::Decision::Answer::Choice
    options = answer.probabilities.map { |item| "{value=#{item.value.inspect}; probability=#{item.probability}}" }
    puts "#{answer.name} (choice): value=#{answer.choice.inspect}; confidence=#{answer.confidence}; " \
      "probabilities=[#{options.join(", ")}]"
  when OpenAI::Models::Decision::Answer::Score
    options = answer.probabilities.map do |item|
      "{label=#{item.label}; value=#{item.value}; probability=#{item.probability}}"
    end
    puts "#{answer.name} (score): score=#{answer.score}; confidence=#{answer.confidence}; " \
      "probabilities=[#{options.join(", ")}]"
  when OpenAI::Models::Decision::Answer::Refusal
    puts "#{answer.name} (refusal): send this question for human review"
  else
    raise "Unexpected Decisions answer type"
  end
end
puts "Usage: #{JSON.generate(decision.usage.to_h)}"

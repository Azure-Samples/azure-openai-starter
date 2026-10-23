# frozen_string_literal: true

require "open3"
require "uri"
require "openai"

def probability(value)
  unless value.is_a?(Numeric) && value.finite? && value.between?(0, 1)
    raise "Malformed Decisions response: invalid probability"
  end
  value
end

def nonnegative_integer(value)
  unless value.is_a?(Integer) && value >= 0
    raise "Malformed Decisions response: invalid token count or score level"
  end
  value
end

def answer_name(value)
  unless value.is_a?(String) && !value.strip.empty?
    raise "Malformed Decisions response: invalid answer name"
  end
  value.inspect
end

def choice_value(value)
  unless value.is_a?(String) || value == true || value == false
    raise "Malformed Decisions response: invalid choice value"
  end
  value.inspect
end

def azure_cli_token
  stdout, _stderr, status = Open3.capture3(
    "az", "account", "get-access-token",
    "--resource", "https://cognitiveservices.azure.com",
    "--query", "accessToken", "--output", "tsv"
  )
  unless status.success?
    raise "Azure CLI token acquisition failed (exit #{status.exitstatus}). Run az login and try again."
  end
  token = stdout.strip
  raise "Azure CLI returned an empty access token" if token.empty?

  token
rescue Errno::ENOENT
  raise "Azure CLI is required without AZURE_OPENAI_API_KEY. Install it and run az login.", cause: nil
end

endpoint = ENV["AZURE_OPENAI_ENDPOINT"]
if endpoint.nil? || endpoint.strip.empty?
  raise "AZURE_OPENAI_ENDPOINT environment variable is required"
end
api_key = ENV["AZURE_OPENAI_API_KEY"]
use_key = !api_key.nil? && !api_key.empty?
uri = URI.parse(endpoint)
loopback = ["localhost", "127.0.0.1", "::1"].include?(uri.hostname&.downcase)
unless uri.host && uri.userinfo.nil? && uri.query.nil? && uri.fragment.nil? && uri.path.delete("/").empty?
  raise "AZURE_OPENAI_ENDPOINT must be the Azure resource root URL"
end
unless uri.is_a?(URI::HTTPS) || (uri.is_a?(URI::HTTP) && loopback && use_key)
  raise "AZURE_OPENAI_ENDPOINT must use HTTPS (HTTP loopback is allowed with an API key)"
end
model = ENV.fetch("AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME", "gpt-6-luna")
raise "AZURE_OPENAI_DECISIONS_DEPLOYMENT_NAME must not be empty" if model.strip.empty?
client = OpenAI::Client.new(
  api_key: use_key ? api_key : azure_cli_token,
  base_url: "#{endpoint.sub(%r{/+\z}, "")}/openai/v1/",
  log_level: :off
)

begin
  # [START decisions_request]
  result = client.decisions.create(
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
  raise "Decisions HTTP #{error.status}: #{error.body.inspect}", cause: nil
end

unless result.answers.is_a?(Array) && !result.answers.empty?
  raise "Decisions response has empty or invalid answers"
end
unless result.usage.is_a?(OpenAI::Models::Decision::Usage)
  raise "Decisions response is missing usage"
end
nonnegative_integer(result.usage.input_tokens)
nonnegative_integer(result.usage.output_tokens)
nonnegative_integer(result.usage.total_tokens)
unless result.model.is_a?(String) && !result.model.empty?
  raise "Decisions response is missing model"
end

lines = result.answers.map do |answer|
  case answer
  when OpenAI::Models::Decision::Answer::Predicate
    "#{answer_name(answer.name)} (predicate): probability=#{probability(answer.probability)}"
  when OpenAI::Models::Decision::Answer::Choice
    unless answer.probabilities.is_a?(Array)
      raise "Malformed Decisions response: invalid choice probabilities"
    end
    answer.probabilities.each do |item|
      choice_value(item.value)
      probability(item.probability)
    end
    "#{answer_name(answer.name)} (choice): value=#{choice_value(answer.choice)}; confidence=#{probability(answer.confidence)}"
  when OpenAI::Models::Decision::Answer::Score
    unless answer.score.is_a?(Numeric) && answer.score.finite? && answer.probabilities.is_a?(Array)
      raise "Malformed Decisions response: invalid score"
    end
    answer.probabilities.each do |item|
      answer_name(item.label)
      nonnegative_integer(item.value)
      probability(item.probability)
    end
    "#{answer_name(answer.name)} (score): score=#{answer.score}; confidence=#{probability(answer.confidence)}"
  when OpenAI::Models::Decision::Answer::Refusal
    "#{answer_name(answer.name)} (refusal): refused"
  else
    raise "Unknown Decisions answer type"
  end
end
puts lines

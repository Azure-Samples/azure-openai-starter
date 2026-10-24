# frozen_string_literal: true

require "open3"
require "uri"
require "openai"

def image_input(args)
  return nil if args.empty?

  unless args.length == 2 && args[0] == "--image" && !args[1].strip.empty?
    raise "Usage: bundle exec ruby decisions_example.rb [--image PATH_OR_HTTPS_URL]"
  end
  source = args[1]
  if source.include?("://")
    begin
      image = URI.parse(source)
    rescue URI::InvalidURIError
      raise "Image URL must be a valid HTTPS URL", cause: nil
    end
    unless image.is_a?(URI::HTTPS) && image.host && !image.host.empty? &&
        image.userinfo.nil? && image.fragment.nil?
      raise "Image URL must use HTTPS with a host, no credentials, and no fragment"
    end
    return source
  end
  mime = case File.extname(source).downcase
  when ".png" then "image/png"
  when ".jpg", ".jpeg" then "image/jpeg"
  when ".webp" then "image/webp"
  when ".gif" then "image/gif"
  else raise "Image file must be PNG, JPEG, WebP, or GIF"
  end
  max_bytes = 32 * 1024 * 1024
  begin
    data = File.open(source, "rb") do |file|
      unless file.stat.file?
        raise "Image file must be a readable regular file"
      end
      unless file.size.positive? && file.size <= max_bytes
        raise "Image file must be nonempty and at most 32 MiB"
      end
      bytes = file.read(max_bytes + 1)
      if bytes.nil? || bytes.empty? || bytes.bytesize > max_bytes
        raise "Image file must be nonempty and at most 32 MiB"
      end
      bytes
    end
  rescue SystemCallError, IOError
    raise "Image file must exist and be readable", cause: nil
  end
  "data:#{mime};base64,#{[data].pack("m0")}"
end

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

image_url = image_input(ARGV)
with_image = !image_url.nil?
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
# Azure deployment name; it must point to GPT-6 Luna.
model = ENV.fetch("AZURE_OPENAI_DEPLOYMENT", "gpt-6-luna")
raise "AZURE_OPENAI_DEPLOYMENT must not be empty" if model.strip.empty?
predicate_name = with_image ? "visible_damage" : "refund_requested"
choice_name = with_image ? "category" : "department"
# Create one client and reuse its connections for subsequent requests.
client = OpenAI::Client.new(
  api_key: use_key ? api_key : azure_cli_token,
  base_url: "#{endpoint.sub(%r{/+\z}, "")}/openai/v1/",
  log_level: :off
)

begin
  # Batch all three questions in one call.
  # [START decisions_request]
  result = client.decisions.create(
    model: model,
    input: with_image ? [
      {
        role: "user",
        content: [
          {type: "input_text", text: "Inspect the photo for visible damage and classify the main object."},
          {type: "input_image", image_url: image_url}
        ]
      }
    ] : "I was charged twice for order 123. Please refund the duplicate charge.",
    questions: [
      {
        type: "predicate",
        name: predicate_name,
        instructions: with_image ?
          "Does the photo show visible damage to the main object?" :
          "Does the customer request a refund?"
      },
      {
        type: "choice",
        name: choice_name,
        instructions: with_image ?
          "Which category best describes the main object?" :
          "Which department should handle this request?",
        choices: [
          {value: with_image ? "parcel" : "billing",
           description: with_image ? "A package or parcel." : "Payments and refunds."},
          {value: with_image ? "vehicle" : "technical",
           description: with_image ? "A vehicle." : "Product problems."},
          {value: "other",
           description: with_image ? "None of these categories." : "Other requests."}
        ]
      },
      {
        type: "score",
        name: "severity",
        instructions: with_image ? "How severe is the visible damage?" : "How severe is this issue?",
        levels: [
          {label: "Low",
           description: with_image ? "No damage or minor cosmetic damage." : "Minor inconvenience."},
          {label: "Medium",
           description: with_image ? "Visible damage that needs attention." : "Needs attention."},
          {label: "High",
           description: with_image ? "Severe damage or loss of function." : "Urgent action needed."}
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
input_tokens = nonnegative_integer(result.usage.input_tokens)
output_tokens = nonnegative_integer(result.usage.output_tokens)
total_tokens = nonnegative_integer(result.usage.total_tokens)
unless result.model.is_a?(String) && !result.model.strip.empty?
  raise "Decisions response is missing model"
end

expected_names = [predicate_name, choice_name, "severity"]
seen = {}
lines = result.answers.flat_map do |answer|
  raise "Unknown Decisions answer type" unless answer.respond_to?(:name)

  name = answer_name(answer.name)
  unless expected_names.include?(answer.name)
    raise "Decisions response has an unknown answer name: #{name}"
  end
  raise "Decisions response has a duplicate answer: #{name}" if seen[answer.name]

  seen[answer.name] = true
  case answer
  when OpenAI::Models::Decision::Answer::Predicate
    ["#{name} (predicate): probability=#{probability(answer.probability)}"]
  when OpenAI::Models::Decision::Answer::Choice
    unless answer.probabilities.is_a?(Array) && !answer.probabilities.empty?
      raise "Malformed Decisions response: invalid choice probabilities"
    end
    options = answer.probabilities.map do |item|
      "{value=#{choice_value(item.value)}; probability=#{probability(item.probability)}}"
    end
    ["#{name} (choice): value=#{choice_value(answer.choice)}; confidence=#{probability(answer.confidence)}; " \
      "probabilities=[#{options.join(", ")}]"]
  when OpenAI::Models::Decision::Answer::Score
    unless answer.score.is_a?(Numeric) && answer.score.finite? &&
        answer.probabilities.is_a?(Array) && !answer.probabilities.empty?
      raise "Malformed Decisions response: invalid score"
    end
    options = answer.probabilities.map do |item|
      "{label=#{answer_name(item.label)}; " \
        "value=#{nonnegative_integer(item.value)}; probability=#{probability(item.probability)}}"
    end
    ["#{name} (score): score=#{answer.score}; confidence=#{probability(answer.confidence)}; " \
      "probabilities=[#{options.join(", ")}]"]
  when OpenAI::Models::Decision::Answer::Refusal
    ["#{name} (refusal): refused"]
  else
    raise "Unknown Decisions answer type"
  end
end
expected_names.each do |name|
  raise "Decisions response is missing answer: #{name}" unless seen[name]
end
usage_line = "Usage: input_tokens=#{input_tokens}; output_tokens=#{output_tokens}; total_tokens=#{total_tokens}"
input_details = result.usage.input_tokens_details
unless input_details.nil?
  unless input_details.is_a?(OpenAI::Models::Decision::Usage::InputTokensDetails)
    raise "Malformed Decisions response: invalid input_tokens_details"
  end
  unless input_details.cached_tokens.nil?
    usage_line += "; cached_tokens=#{nonnegative_integer(input_details.cached_tokens)}"
  end
  unless input_details.cache_write_tokens.nil?
    usage_line += "; cache_write_tokens=#{nonnegative_integer(input_details.cache_write_tokens)}"
  end
end
output_details = result.usage.output_tokens_details
unless output_details.nil?
  unless output_details.is_a?(OpenAI::Models::Decision::Usage::OutputTokensDetails)
    raise "Malformed Decisions response: invalid output_tokens_details"
  end
  unless output_details.reasoning_tokens.nil?
    usage_line += "; reasoning_tokens=#{nonnegative_integer(output_details.reasoning_tokens)}"
  end
end
lines << usage_line
puts lines

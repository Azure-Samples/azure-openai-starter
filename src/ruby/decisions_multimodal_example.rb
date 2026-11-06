# frozen_string_literal: true

require "json"
require "open3"
require "openai"

# A public-domain NASA photo. Azure fetches an HTTPS URL itself.
DEFAULT_IMAGE = "https://raw.githubusercontent.com/scikit-image/scikit-image/v0.25.2/skimage/data/astronaut.png"
MEDIA_TYPES = {
  ".png" => "image/png", ".jpg" => "image/jpeg", ".jpeg" => "image/jpeg",
  ".webp" => "image/webp", ".gif" => "image/gif"
}.freeze

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

# Pass your own HTTPS image URL or the path to an image file.
image = ARGV[0] || DEFAULT_IMAGE
unless image.start_with?("https://")
  # A local file is sent inline as a base64 data URL.
  image = "data:#{MEDIA_TYPES[File.extname(image).downcase]};base64,#{[File.binread(image)].pack("m0")}"
end

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
    input: [
      {
        role: "user",
        content: [
          {type: "input_text", text: "Inspect the photo for visible damage and classify the main object."},
          {type: "input_image", image_url: image}
        ]
      }
    ],
    questions: [
      {
        type: "predicate",
        name: "visible_damage",
        instructions: "Does the photo show visible damage to the main object?"
      },
      {
        type: "choice",
        name: "category",
        instructions: "Which category best describes the main object?",
        choices: [
          {value: "parcel", description: "A package or parcel."},
          {value: "vehicle", description: "A vehicle."},
          {value: "other", description: "None of these categories."}
        ]
      },
      {
        type: "score",
        name: "severity",
        instructions: "How severe is the visible damage?",
        levels: [
          {label: "Low", description: "No damage or minor cosmetic damage."},
          {label: "Medium", description: "Visible damage that needs attention."},
          {label: "High", description: "Severe damage or loss of function."}
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

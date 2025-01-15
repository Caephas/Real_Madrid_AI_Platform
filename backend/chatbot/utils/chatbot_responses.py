import subprocess


def run_llama_query(query: str) -> str:
    """
    Run a query against the downloaded model using Llama.cpp.
    """
    # Format the query as required
    formatted_query = f"""
    Below is a question and its corresponding factual answer. Provide an accurate response to the question.

    ### Question:
    {query}

    ### Answer:
    """

    # Run the Llama.cpp CLI with the query
    process = subprocess.run(
        [
            "llama-cli",  # Replace with the path to your llama.cpp binary if necessary
            "--model", "/Users/caephas/Downloads/unsloth.Q8_0.gguf",  # Replace with your local GGUF model path
            "-p", formatted_query
        ],
        capture_output=True,
        text=True
    )

    # Extract and return the response
    response = process.stdout.strip()
    return response
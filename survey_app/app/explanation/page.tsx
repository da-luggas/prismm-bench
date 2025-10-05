"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ExplanationPage() {
	return (
		<div className="min-h-screen bg-background p-4">
			<div className="max-w-4xl mx-auto space-y-6">
				<div className="text-center">
					<h1 className="text-3xl font-bold mb-2">
						Understanding the Answer Format
					</h1>
					<p className="text-muted-foreground">
						Before we begin the survey, please take a moment to familiarize
						yourself with the format of the answer options you will encounter.
					</p>
				</div>

				<Card>
					<CardHeader>
						<CardTitle>Evidence-Claim JSON Format</CardTitle>
					</CardHeader>
					<CardContent className="space-y-4">
						<p>
							Each answer option will be presented in a structured JSON format.
							The options are not full sentences, rather a key-value pair
							format. When answering the survey, you should interpret the
							statements by grounding them together with the attribute in the
							relevant source or in general scientific expectations to fully
							understand the meaning of the statements. Here is the general
							format:
						</p>

						<div className="bg-muted p-4 rounded-lg">
							<pre className="overflow-x-auto">
								{`{
  "letter": "A" | "B" | "C" | "D",
  "attribute": str,
  "claim": {
    "source": "expectation" | str,
    "statement": str
  },
  "evidence": {
    "source": str,
    "statement": str
  },
}`}
							</pre>
						</div>

						<div className="space-y-6">
							<div>
								<p className="py-3">
									There are two patterns the JSON can follow:
								</p>
								<h3 className="text-lg font-semibold mb-3">
									Pattern 1: Claim Contradicted by Evidence
								</h3>
								<p className="mb-3">
									One part of the answer makes a claim that is contradicted by
									evidence in another part regarding the attribute.
								</p>
								<div className="bg-muted p-4 rounded-lg">
									<p className="text-sm font-medium mb-2">Example:</p>
									<pre className="overflow-x-auto">
										{`{
  "letter": "C",
  "attribute": "optimal trade-off",
  "claim": {
    "source": "caption",
    "statement": "at 128 tokens"
  },
  "evidence": {
    "source": "plot",
    "statement": "not visible at 128 tokens"
  },
}`}
									</pre>
								</div>
							</div>
							<div className="bg-green-50 border-l-4 border-green-300 p-4 rounded">
								<p className="text-sm text-green-800">
									<strong>Read This As:</strong> There is a <u>claim</u> made in
									the <u>caption</u> about the <u>attribute</u>{" "}
									<i>"optimal trade-off"</i> and the claim is that the{" "}
									<i>"optimal trade-off"</i> is "at 128 tokens", but there is{" "}
									<u>evidence</u> in the <u>plot</u> that contradicts this
									claim, showing that the <i>"optimal trade-off"</i> is{" "}
									<i>"not visible at 128 tokens"</i>.
								</p>
							</div>

							<div>
								<h3 className="text-lg font-semibold mb-3">
									Pattern 2: Claim Contradicts Scientific Expectations
								</h3>
								<p className="mb-3">
									One part of the answer makes a claim that contradicts common
									expectations of scientific correctness regarding the
									attribute. In this case, the claim's source is always
									"expectation". You can also read it as "common sense".
								</p>
								<div className="bg-muted p-4 rounded-lg">
									<p className="text-sm font-medium mb-2">Example:</p>
									<pre className="overflow-x-auto">
										{`{
  "letter": "A",
  "attribute": "legend",
  "claim": {
    "source": "expectation",
    "statement": "shouldn't occlude plot"
  },
  "evidence": {
    "source": "figure_8",
    "statement": "occludes plot"
  },
}`}
									</pre>
								</div>
							</div>
						</div>

						<div className="bg-green-50 border-l-4 border-green-300 p-4 rounded">
							<p className="text-sm text-green-800">
								<strong>Read This As:</strong> There is a <u>claim</u> based on{" "}
								<u>scientific expectation</u> about the <u>attribute</u>{" "}
								<i>"legend"</i> and the claim is that the <i>"legend"</i>{" "}
								<i>"shouldn't occlude"</i> the plot, but there is{" "}
								<u>evidence</u> in the <u>Figure 8</u> that contradicts this
								claim, showing that the <i>"legend"</i> <i>occludes</i> the
								plot.
							</p>
						</div>
					</CardContent>
				</Card>

				<div className="text-center">
					<Button
						onClick={() => {
							window.location.href = "/survey";
						}}
						size="lg"
						className="px-8 cursor-pointer"
					>
						Continue to Survey
					</Button>
				</div>
			</div>
		</div>
	);
}

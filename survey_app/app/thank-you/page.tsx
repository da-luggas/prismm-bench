"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle } from "lucide-react";

export default function ThankYouPage() {
	const [results, setResults] = useState<any[]>([]);

	useEffect(() => {
		const savedResults = localStorage.getItem("surveyResults");
		if (savedResults) {
			setResults(JSON.parse(savedResults));
		}
	}, []);

	const correctAnswers = results.filter((r) => r.is_correct).length;
	const totalQuestions = results.length;

	return (
		<div className="min-h-screen bg-background flex items-center justify-center p-4">
			<Card className="w-full max-w-2xl">
				<CardHeader className="text-center">
					<div className="mx-auto mb-4 w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
						<CheckCircle className="w-8 h-8 text-green-600" />
					</div>
					<CardTitle className="text-3xl font-bold">Thank You!</CardTitle>
				</CardHeader>
				<CardContent className="text-center space-y-6">
					<div>
						<p className="text-lg mb-4">
							Thank you for participating in our research survey. Your responses
							have been recorded.
						</p>

						{totalQuestions > 0 && (
							<div className="bg-muted rounded-lg p-4 mb-4">
								<p className="font-medium">Your Performance:</p>
								<p className="text-2xl font-bold text-primary">
									{correctAnswers} / {totalQuestions}
								</p>
								<p className="text-sm text-muted-foreground">
									({Math.round((correctAnswers / totalQuestions) * 100)}%
									correct)
								</p>
							</div>
						)}
					</div>

					<Button
						className="cursor-pointer"
						onClick={() => (window.location.href = "/survey")}
						size="lg"
					>
						Try Another Round
					</Button>
				</CardContent>
			</Card>
		</div>
	);
}

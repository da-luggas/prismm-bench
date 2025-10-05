"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface UserInfo {
  email: string
  academicField: string
  academicLevel: string
  aiExposure: string
}

export default function WelcomePage() {
  const [userInfo, setUserInfo] = useState<UserInfo>({
    email: "",
    academicField: "",
    academicLevel: "",
    aiExposure: "",
  })
  const [consentChecked, setConsentChecked] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Store user info
    localStorage.setItem("userInfo", JSON.stringify(userInfo))
    // Set cookies for middleware check
    document.cookie = `user-answered=true; path=/; samesite=lax`;
    document.cookie = `checkbox-answered=true; path=/; samesite=lax`;
    // Navigate to explanation page
    window.location.href = "/explanation"
  }

  const isFormValid = userInfo.email && userInfo.academicField && userInfo.academicLevel && userInfo.aiExposure && consentChecked

  const academicFields = [
    "Computer Science & Artificial Intelligence",
    "Engineering",
    "Natural Sciences (Biology, Chemistry, Physics)",
    "Social Sciences (Psychology, Sociology, Economics)",
    "Health Sciences / Medicine",
    "Education",
    "Business and Management",
    "Mathematics & Statistics",
    "Humanities",
  ]

  const academicLevels = [
    "Undergraduate (Bachelor's)",
    "Graduate (Master's)",
    "Doctoral (PhD)",
    "Postdoctoral Researchers / Early Career Researchers",
    "Faculty / Professors / Research Scientists",
  ]

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">Research Survey</CardTitle>
          <CardDescription className="text-lg">
            Help us create a benchmark dataset for multimodal inconsistencies in academic papers.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="prose prose-sm max-w-none">
            <p className="mb-4">
              This survey is part of a research project aimed at evaluating the performance of multimodal large language models (MLLMs) in identifying inconsistencies in academic literature. Your participation will help create a human baseline score for these models.
            </p>
            <p className="mb-4">
              The survey consists of 10 questions and should take approximately 45 minutes to complete. You will see a series of image and text excerpts from research papers that contain an inconsistency. Your task is to identify the inconsistency and pick the correct answer from the options provided.
            </p>
            <p className="mb-4">
              All personal data entered will be handled with strict confidentiality and won't be published. Your answers will be used together with those from all other participants to calculate an average performance of all human participants. Once this baseline is established, all data will be deleted.
            </p>
          </div>

        <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 px-4 py-3 rounded-md">
            <div className="flex">
                <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                </div>
                <div className="ml-3">
                    <p className="text-sm">
                        This survey is best completed on a big screen (e.g., desktop or laptop) to ensure optimal viewing of images and text excerpts.
                    </p>
                </div>
            </div>
        </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email Address *</Label>
              <Input
                id="email"
                type="email"
                placeholder="your.email@example.com"
                value={userInfo.email}
                onChange={(e) => setUserInfo((prev) => ({ ...prev, email: e.target.value }))}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="academic-field">Academic Field *</Label>
              <Select
                value={userInfo.academicField}
                onValueChange={(value) => setUserInfo((prev) => ({ ...prev, academicField: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select your academic field" />
                </SelectTrigger>
                <SelectContent>
                  {academicFields.map((field) => (
                    <SelectItem key={field} value={field}>
                      {field}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="academic-level">Academic Level *</Label>
              <Select
                value={userInfo.academicLevel}
                onValueChange={(value) => setUserInfo((prev) => ({ ...prev, academicLevel: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select your academic level" />
                </SelectTrigger>
                <SelectContent>
                  {academicLevels.map((level) => (
                    <SelectItem key={level} value={level}>
                      {level}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="ai-exposure">Exposure to Artificial Intelligence *</Label>
              <Select
                value={userInfo.aiExposure}
                onValueChange={(value) => setUserInfo((prev) => ({ ...prev, aiExposure: value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select your level of AI exposure" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="beginner">
                  <div className="flex flex-col items-start text-left">
                    <span className="font-medium">Beginner</span>
                    <span className="text-xs text-muted-foreground">
                    Limited or no familiarity with AI scientific literature; basic understanding or exposure
                    </span>
                  </div>
                  </SelectItem>
                  <SelectItem value="intermediate">
                  <div className="flex flex-col items-start text-left">
                    <span className="font-medium">Intermediate</span>
                    <span className="text-xs text-muted-foreground">
                    Moderate familiarity; can understand and use AI scientific literature with some confidence
                    </span>
                  </div>
                  </SelectItem>
                  <SelectItem value="advanced">
                  <div className="flex flex-col items-start text-left">
                    <span className="font-medium">Advanced</span>
                    <span className="text-xs text-muted-foreground">
                    Strong proficiency; comfortable reading, interpreting, and critically evaluating AI scientific
                    literature
                    </span>
                  </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-start space-x-2">
              <input
                id="consent-checkbox"
                type="checkbox"
                checked={consentChecked}
                onChange={(e) => setConsentChecked(e.target.checked)}
                required
                className="mt-1"
              />
              <Label htmlFor="consent-checkbox" className="flex-1 cursor-pointer">
                I have read all instructions and information above, and I confirm that I will handle the quiz to the best of my capabilities and take it seriously.
              </Label>
            </div>

            <Button className="cursor-pointer w-full" type="submit" size="lg" disabled={!isFormValid}>
              Start Survey
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

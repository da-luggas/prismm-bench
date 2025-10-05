"use client"

import React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { FileText, Download } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import AnnotationInterface from "@/components/annotation-interface"

interface PaperData {
  has_inconsistency: boolean
  inconsistencies: string[]
}

interface RawInputData {
  [paper_id: string]: PaperData
}

interface ProcessedInputData {
  [paper_id: string]: string[]
}

interface AnnotatedInconsistency {
  inconsistency_parts: Array<{
    type: "image" | "text"
    image_id?: string // Reference to saved image instead of base64
    content?: string
    page: number
    bbox?: {
      x: number
      y: number
      width: number
      height: number
    }
    line?: number
  }>
  review_text: string
  category: string
  description: string
  skipped?: boolean // Added to allow marking skipped inconsistencies
}

interface OutputData {
  [paper_id: string]: AnnotatedInconsistency[]
}

export default function HomePage() {
  const [inputData, setInputData] = useState<ProcessedInputData | null>(null)
  const [outputData, setOutputData] = useState<OutputData>({})
  const [currentPaperId, setCurrentPaperId] = useState<string>("")
  const [currentInconsistencyIndex, setCurrentInconsistencyIndex] = useState(0)
  const [batchSize, setBatchSize] = useState(50) // Configurable batch size
  const { toast } = useToast()

  const handleInputFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const rawData: RawInputData = JSON.parse(e.target?.result as string)

        // Process the data to only include papers with inconsistencies
        const processedData: ProcessedInputData = {}

        Object.entries(rawData).forEach(([paperId, paperData]) => {
          if (paperData.has_inconsistency && paperData.inconsistencies && paperData.inconsistencies.length > 0) {
            processedData[paperId] = paperData.inconsistencies
          }
        })

        // Check if we have any papers with inconsistencies
        if (Object.keys(processedData).length === 0) {
          toast({
            title: "No inconsistencies found",
            description: "The uploaded file contains no papers with inconsistencies to annotate",
            variant: "destructive",
          })
          return
        }

        setInputData(processedData)

        const totalInconsistencies = Object.values(processedData).reduce(
          (total, inconsistencies) => total + inconsistencies.length,
          0,
        )

        toast({
          title: "File uploaded successfully",
          description: `Loaded ${Object.keys(processedData).length} papers with ${totalInconsistencies} inconsistencies`,
        })
      } catch (error) {
        toast({
          title: "Error",
          description: "Invalid JSON file format",
          variant: "destructive",
        })
      }
    }
    reader.readAsText(file)
  }

  const handleOutputFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string)
        setOutputData(data)
        toast({
          title: "Progress file loaded",
          description: "Previous annotations restored",
        })
      } catch (error) {
        toast({
          title: "Error",
          description: "Invalid progress file format",
          variant: "destructive",
        })
      }
    }
    reader.readAsText(file)
  }

  const exportResults = async () => {
    try {
      // Create a zip file containing both JSON and images
      const response = await fetch("/api/export-annotations", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(outputData),
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.href = url
        link.download = "annotated_inconsistencies.zip"
        link.click()
        URL.revokeObjectURL(url)
      } else {
        // Fallback to JSON-only export
        const dataStr = JSON.stringify(outputData, null, 2)
        const dataBlob = new Blob([dataStr], { type: "application/json" })
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement("a")
        link.href = url
        link.download = "annotated_inconsistencies.json"
        link.click()
        URL.revokeObjectURL(url)
      }
    } catch (error) {
      // Fallback to JSON-only export
      const dataStr = JSON.stringify(outputData, null, 2)
      const dataBlob = new Blob([dataStr], { type: "application/json" })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement("a")
      link.href = url
      link.download = "annotated_inconsistencies.json"
      link.click()
      URL.revokeObjectURL(url)
    }
  }

  const exportBatch = async () => {
    const completedCount = getCompletedInconsistencies()
    if (completedCount === 0) {
      toast({
        title: "No annotations to export",
        description: "Complete some annotations before exporting a batch",
        variant: "destructive",
      })
      return
    }

    if (completedCount % batchSize === 0 || completedCount >= getTotalInconsistencies()) {
      await exportResults()
      toast({
        title: "Batch exported",
        description: `Exported ${completedCount} annotations`,
      })
    }
  }

  const getTotalInconsistencies = () => {
    if (!inputData) return 0
    return Object.values(inputData).reduce((total, inconsistencies) => total + inconsistencies.length, 0)
  }

  const getCompletedInconsistencies = () => {
    if (!inputData) return 0
    let completed = 0
    Object.keys(inputData).forEach((paperId) => {
      const paperInconsistencies = inputData[paperId]
      const annotatedCount = outputData[paperId]?.length || 0
      completed += Math.min(annotatedCount, paperInconsistencies.length)
    })
    return completed
  }

  // Add a new function to count valid inconsistencies (not skipped)
  const getValidInconsistencies = () => {
    if (!inputData) return 0
    let valid = 0
    Object.keys(outputData).forEach((paperId) => {
      const annotations = outputData[paperId] || []
      valid += annotations.filter(ann => !ann.skipped).length
    })
    return valid
  }

  const getCurrentInconsistency = () => {
    if (!inputData || !currentPaperId) return null
    return inputData[currentPaperId]?.[currentInconsistencyIndex]
  }

  const isAllCompleted = () => {
    if (!inputData) return false

    for (const paperId of Object.keys(inputData)) {
      const paperInconsistencies = inputData[paperId]
      const annotatedCount = outputData[paperId]?.length || 0
      if (annotatedCount < paperInconsistencies.length) {
        return false
      }
    }
    return true
  }

  const saveAnnotation = async (annotation: AnnotatedInconsistency) => {
    const newOutputData = {
      ...outputData,
      [currentPaperId]: [...(outputData[currentPaperId] || []), annotation],
    }

    setOutputData(newOutputData)

    // Save progress incrementally to localStorage (only metadata, not images)
    try {
      const progressData = {
        ...newOutputData,
        // Remove image data for localStorage to save space
        [currentPaperId]: newOutputData[currentPaperId].map((ann) => ({
          ...ann,
          inconsistency_parts: ann.inconsistency_parts.map((part) => ({
            ...part,
            // Keep only image_id reference, not base64 data
            base64: undefined,
          })),
        })),
      }
      localStorage.setItem("annotation_progress", JSON.stringify(progressData))
    } catch (error) {
      console.error("Failed to save progress to localStorage:", error)
    }

    // Auto-export every batch_size annotations
    const completedCount = getCompletedInconsistencies() + 1
    if (completedCount % batchSize === 0) {
      await exportBatch()
    }

    // Call API to remove file for the current paper
    // try {
    //   await fetch(`http://localhost:8080/api/remove-paper?paper_id=${encodeURIComponent(currentPaperId)}`, {
    //     method: "GET",
    //   })
    // } catch (error) {
    //   console.error("Failed to call /api/remove-paper:", error)
    // }

    // Move to next inconsistency
    const currentPaperInconsistencies = inputData![currentPaperId]
    if (currentInconsistencyIndex < currentPaperInconsistencies.length - 1) {
      setCurrentInconsistencyIndex((prev) => prev + 1)
    } else {
      // Move to next paper
      const paperIds = Object.keys(inputData!)
      const currentPaperIndex = paperIds.indexOf(currentPaperId)
      if (currentPaperIndex < paperIds.length - 1) {
        const nextPaperId = paperIds[currentPaperIndex + 1]
        setCurrentPaperId(nextPaperId)
        setCurrentInconsistencyIndex(0)
      } else {
        // All papers completed - clear current state to show completion screen
        setCurrentPaperId("")
        setCurrentInconsistencyIndex(0)
      }
    }

    toast({
      title: "Annotation saved",
      description: `Moving to next inconsistency (${completedCount}/${getTotalInconsistencies()})`,
    })
  }

  const skipCurrentInconsistency = async () => {
    if (!inputData || !currentPaperId) return
    const currentInconsistency = getCurrentInconsistency()
    if (!currentInconsistency) return

    // Create a skipped annotation entry
    const skippedAnnotation: AnnotatedInconsistency = {
      inconsistency_parts: [],
      review_text: '',
      category: '',
      description: '',
      skipped: true as any, // TypeScript workaround, will be present in JSON
    }
    await saveAnnotation(skippedAnnotation)
    toast({
      title: "Inconsistency skipped",
      description: `Skipped inconsistency (${getCompletedInconsistencies() + 1}/${getTotalInconsistencies()})`,
    })
  }

  // Load saved progress on component mount
  React.useEffect(() => {
    try {
      const savedProgress = localStorage.getItem("annotation_progress")
      if (savedProgress) {
        const parsedProgress = JSON.parse(savedProgress)
        setOutputData(parsedProgress)
      }
    } catch (error) {
      console.error("Failed to load saved progress:", error)
    }
  }, [])

  // Effect to find the next inconsistency to annotate when data loads
  React.useEffect(() => {
    if (!inputData || Object.keys(outputData).length === 0) {
      // If we don't have progress, we start from the beginning (which is the default)
      if (inputData) {
        const firstPaperId = Object.keys(inputData)[0]
        setCurrentPaperId(firstPaperId)
        setCurrentInconsistencyIndex(0)
      }
      return
    }

    let foundNext = false
    for (const paperId of Object.keys(inputData)) {
      const paperInconsistencies = inputData[paperId]
      const annotatedCount = outputData[paperId]?.length || 0

      if (annotatedCount < paperInconsistencies.length) {
        setCurrentPaperId(paperId)
        setCurrentInconsistencyIndex(annotatedCount)
        foundNext = true
        break
      }
    }

    if (!foundNext) {
      // All inconsistencies are annotated
      setCurrentPaperId("")
      setCurrentInconsistencyIndex(0)
    }
  }, [inputData, outputData])

  if (!inputData) {
    return (
      <div className="container mx-auto p-6 max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-6 h-6" />
              Paper Inconsistency Annotation Tool
            </CardTitle>
            <CardDescription>
              Upload your inconsistency data to start annotating visual inconsistencies in scientific papers
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="batch-size">Batch Size for Auto-Export</Label>
              <Input
                id="batch-size"
                type="number"
                min="10"
                max="200"
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
              />
              <p className="text-sm text-muted-foreground">
                Automatically export results every N annotations to prevent data loss
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="progress-file">Resume Previous Session (Optional)</Label>
              <Input id="progress-file" type="file" accept=".json" onChange={handleOutputFileUpload} />
              <p className="text-sm text-muted-foreground">
                Upload your previous annotation progress to continue where you left off
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="input-file">Upload Inconsistency Data (JSON)</Label>
              <Input id="input-file" type="file" accept=".json" onChange={handleInputFileUpload} />
              <p className="text-sm text-muted-foreground">
                Upload the JSON file containing papers with has_inconsistency and inconsistencies fields
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const currentInconsistency = getCurrentInconsistency()
  const totalInconsistencies = getTotalInconsistencies()
  const completedInconsistencies = getCompletedInconsistencies()
  const validInconsistencies = getValidInconsistencies() // Add this line

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Paper Inconsistency Annotation</h1>
        <div className="flex gap-2">
          <Button onClick={exportBatch} variant="outline" className="flex items-center gap-2 bg-transparent">
            <Download className="w-4 h-4" />
            Export Batch ({completedInconsistencies})
          </Button>
          <Button onClick={exportResults} className="flex items-center gap-2">
            <Download className="w-4 h-4" />
            Export All
          </Button>
        </div>
      </div>

      {/* Add progress statistics */}
      <div className="mb-4 p-4 bg-muted rounded-lg">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <h3 className="font-medium">Completed</h3>
            <p className="text-lg">{completedInconsistencies}/{totalInconsistencies}</p>
            <p className="text-xs text-muted-foreground">({((completedInconsistencies/totalInconsistencies)*100).toFixed(1)}%)</p>
          </div>
          <div>
            <h3 className="font-medium">Valid Inconsistencies</h3>
            <p className="text-lg">{validInconsistencies}/{completedInconsistencies}</p>
            <p className="text-xs text-muted-foreground">({completedInconsistencies > 0 ? ((validInconsistencies/completedInconsistencies)*100).toFixed(1) : 0}%)</p>
          </div>
          <div>
            <h3 className="font-medium">Skipped</h3>
            <p className="text-lg">{completedInconsistencies - validInconsistencies}/{completedInconsistencies}</p>
            <p className="text-xs text-muted-foreground">({completedInconsistencies > 0 ? (((completedInconsistencies - validInconsistencies)/completedInconsistencies)*100).toFixed(1) : 0}%)</p>
          </div>
        </div>
      </div>

      {/* Skip button above the annotation interface */}
      {currentInconsistency && !isAllCompleted() && (
        <div className="flex justify-end mb-4">
          <Button variant="secondary" onClick={skipCurrentInconsistency}>
            Skip This Inconsistency
          </Button>
        </div>
      )}

      {currentInconsistency && !isAllCompleted() && (
        <AnnotationInterface
          paperId={currentPaperId}
          inconsistencyText={currentInconsistency}
          progress={{
            current: completedInconsistencies,
            total: totalInconsistencies,
          }}
          onSave={saveAnnotation}
        />
      )}

      {(!currentInconsistency || isAllCompleted()) && (
        <Card>
          <CardContent className="p-6 text-center">
            <h2 className="text-xl font-semibold mb-2">All Inconsistencies Annotated!</h2>
            <p className="text-muted-foreground mb-4">
              You have completed annotating all {totalInconsistencies} inconsistencies.
            </p>
            <Button onClick={exportResults} className="flex items-center gap-2 mx-auto">
              <Download className="w-4 h-4" />
              Download Final Results
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { FileText, Save } from "lucide-react"
import InconsistencyPanel from "./inconsistency-panel"

interface InconsistencyPart {
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
}

interface AnnotationInterfaceProps {
  paperId: string
  inconsistencyText: string
  progress: {
    current: number
    total: number
  }
  onSave: (annotation: any) => void
}

const INCONSISTENCY_CATEGORIES = [
  "figure-only",
  "table-only",
  "equation-only",
  
  "figure-text",
  "table-text",
  "equation-text",

  "figure-figure",
  "table-table",
  "figure-table",

  "figure-caption",

  "other",
]

export default function AnnotationInterface({
  paperId,
  inconsistencyText,
  progress,
  onSave,
}: AnnotationInterfaceProps) {
  const [enableSecondPanel, setEnableSecondPanel] = useState(false)
  const [firstPart, setFirstPart] = useState<InconsistencyPart>({
    type: "image",
    page: 1,
  })
  const [secondPart, setSecondPart] = useState<InconsistencyPart>({
    type: "image",
    page: 1,
  })
  const [category, setCategory] = useState("")
  const [description, setDescription] = useState("")

  const progressPercentage = (progress.current / progress.total) * 100

  const handleSave = async () => {
    if (!category || !description) {
      alert("Please fill in all required fields")
      return
    }

    const parts = [firstPart]
    if (enableSecondPanel) {
      parts.push(secondPart)
    }

    // Validate parts
    for (const part of parts) {
      if (part.type === "image" && !part.image_id) {
        alert("Please complete all image annotations")
        return
      }
      if (part.type === "text" && !part.content) {
        alert("Please complete all text annotations")
        return
      }
    }

    const annotation = {
      inconsistency_parts: parts,
      review_text: inconsistencyText,
      category,
      description,
    }

    onSave(annotation)

    // Reset form
    setFirstPart({ type: "image", page: 1 })
    setSecondPart({ type: "image", page: 1 })
    setCategory("")
    setDescription("")
    setEnableSecondPanel(false)
  }

  return (
    <div className="space-y-6">
      {/* Progress */}
      <Card>
        <CardContent className="p-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium">Progress</span>
            <span className="text-sm text-muted-foreground">
              {progress.current + 1} of {progress.total}
            </span>
          </div>
          <Progress value={progressPercentage} className="w-full" />
          <div className="text-xs text-muted-foreground mt-1">{progressPercentage.toFixed(1)}% complete</div>
        </CardContent>
      </Card>

      {/* Current Inconsistency Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Current Inconsistency
          </CardTitle>
          <CardDescription>Paper ID: {paperId}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm whitespace-pre-wrap">{inconsistencyText}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* PDF Viewer */}
      <Card>
        <CardHeader>
          <CardTitle>PDF Document</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="w-full h-[80vh] border rounded-lg overflow-hidden">
            <iframe src={`/api/pdf-proxy?paper_id=${paperId}`} className="w-full h-full" title="PDF Viewer" />
          </div>
        </CardContent>
      </Card>

      {/* Inconsistency Panels */}
      <div className="space-y-4">
        <div className="flex items-center space-x-2">
          <Switch id="second-panel" checked={enableSecondPanel} onCheckedChange={setEnableSecondPanel} />
          <Label htmlFor="second-panel">Enable second inconsistency part</Label>
        </div>

        <InconsistencyPanel
          title="First Inconsistency Part"
          part={firstPart}
          onChange={setFirstPart}
          paperId={paperId}
        />

        {enableSecondPanel && (
          <InconsistencyPanel
            title="Second Inconsistency Part"
            part={secondPart}
            onChange={setSecondPart}
            paperId={paperId}
          />
        )}
      </div>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Annotation Metadata</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="category">Inconsistency Category</Label>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger>
                <SelectValue placeholder="Select category" />
              </SelectTrigger>
              <SelectContent>
                {INCONSISTENCY_CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Provide a short description of the inconsistency..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <Button onClick={handleSave} className="w-full flex items-center gap-2">
        <Save className="w-4 h-4" />
        Save Annotation & Continue
      </Button>
    </div>
  )
}

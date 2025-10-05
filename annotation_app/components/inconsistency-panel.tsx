"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { ImageIcon, Type } from "lucide-react"
import ImageCropper from "./image-cropper"

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

interface InconsistencyPanelProps {
  title: string
  part: InconsistencyPart
  onChange: (part: InconsistencyPart) => void
  paperId: string
}

export default function InconsistencyPanel({ title, part, onChange, paperId }: InconsistencyPanelProps) {
  const [pageImage, setPageImage] = useState<string | null>(null)
  const [loadingImage, setLoadingImage] = useState(false)
  const [savedImagePreview, setSavedImagePreview] = useState<string | null>(null)

  const handleTypeChange = (isImage: boolean) => {
    onChange({
      ...part,
      type: isImage ? "image" : "text",
      image_id: undefined,
      content: undefined,
      bbox: undefined,
      line: undefined,
    })
    setSavedImagePreview(null)
  }

  const handlePageChange = (page: string) => {
    const pageNum = Number.parseInt(page)
    onChange({ ...part, page: pageNum })

    if (part.type === "image") {
      loadPageImage(pageNum)
    }
  }

  const loadPageImage = async (page: number) => {
    setLoadingImage(true)
    try {
      const response = await fetch(`http://localhost:8080/api/pdf-to-image?paper_id=${paperId}&page=${page}`)
      if (response.ok) {
        const blob = await response.blob()
        const imageUrl = URL.createObjectURL(blob)
        setPageImage(imageUrl)
      }
    } catch (error) {
      console.error("Failed to load page image:", error)
    } finally {
      setLoadingImage(false)
    }
  }

  const handleCropComplete = async (croppedImage: string, bbox: any) => {
    try {
      // Save image to backend and get reference ID
      const response = await fetch("/api/save-image", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          image_data: croppedImage,
          paper_id: paperId,
          page: part.page,
          bbox: bbox,
        }),
      })

      if (response.ok) {
        const result = await response.json()
        onChange({
          ...part,
          image_id: result.image_id,
          bbox,
        })
        setSavedImagePreview(croppedImage)
      } else {
        // Fallback: use a generated ID and keep image in memory temporarily
        const imageId = `${paperId}_${part.page}_${Date.now()}`
        onChange({
          ...part,
          image_id: imageId,
          bbox,
        })
        setSavedImagePreview(croppedImage)

        // Store temporarily in sessionStorage for this session
        try {
          sessionStorage.setItem(`image_${imageId}`, croppedImage)
        } catch (e) {
          console.warn("Could not store image in sessionStorage:", e)
        }
      }
    } catch (error) {
      console.error("Failed to save image:", error)
      // Fallback: use a generated ID
      const imageId = `${paperId}_${part.page}_${Date.now()}`
      onChange({
        ...part,
        image_id: imageId,
        bbox,
      })
      setSavedImagePreview(croppedImage)
    }
  }

  const handleTextChange = (content: string) => {
    onChange({ ...part, content })
  }

  const handleLineChange = (line: string) => {
    const lineNum = Number.parseInt(line) || 1
    onChange({ ...part, line: lineNum })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {part.type === "image" ? <ImageIcon className="w-5 h-5" /> : <Type className="w-5 h-5" />}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Type Selector */}
        <div className="flex items-center space-x-2">
          <Switch id={`${title}-type`} checked={part.type === "image"} onCheckedChange={handleTypeChange} />
          <Label htmlFor={`${title}-type`}>{part.type === "image" ? "Image" : "Text"} Inconsistency</Label>
        </div>

        {/* Page Selector */}
        <div className="space-y-2">
          <Label>Page Number</Label>
          <Input
            type="number"
            min="1"
            placeholder="Enter page number"
            value={part.page.toString()}
            onChange={(e) => handlePageChange(e.target.value)}
          />
        </div>

        {/* Image Mode */}
        {part.type === "image" && (
          <div className="space-y-4">
            {loadingImage && (
              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground">Loading page image...</p>
              </div>
            )}

            {pageImage && !loadingImage && <ImageCropper imageUrl={pageImage} onCropComplete={handleCropComplete} />}

            {!pageImage && !loadingImage && (
              <Button onClick={() => loadPageImage(part.page)} variant="outline" className="w-full">
                Load Page {part.page} for Cropping
              </Button>
            )}

            {savedImagePreview && (
              <div className="space-y-2">
                <Label>Saved Image Preview</Label>
                <div className="text-xs text-muted-foreground mb-2">Image ID: {part.image_id}</div>
                <img
                  src={savedImagePreview || "/placeholder.svg"}
                  alt="Cropped inconsistency"
                  className="max-w-full h-auto border rounded max-h-32 object-contain"
                />
              </div>
            )}
          </div>
        )}

        {/* Text Mode */}
        {part.type === "text" && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Text Content</Label>
              <Textarea
                placeholder="Paste the inconsistent text here..."
                value={part.content || ""}
                onChange={(e) => handleTextChange(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>Line Number</Label>
              <Input
                type="number"
                min="1"
                placeholder="Enter line number"
                value={part.line || ""}
                onChange={(e) => handleLineChange(e.target.value)}
              />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

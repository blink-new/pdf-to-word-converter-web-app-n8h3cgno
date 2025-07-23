import { useState, useRef } from 'react'
import { Upload, FileText, Download, Loader2, CheckCircle, AlertCircle, Image, Merge, RefreshCw } from 'lucide-react'
import { Button } from './components/ui/button'
import { Card, CardContent } from './components/ui/card'
import { Progress } from './components/ui/progress'
import { Alert, AlertDescription } from './components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs'

interface ConversionStatus {
  status: 'idle' | 'uploading' | 'converting' | 'success' | 'error'
  message: string
  downloadUrl?: string
}

type ConversionTool = 'pdf-to-word' | 'word-to-pdf' | 'merge-pdf' | 'image-to-pdf'

interface ToolConfig {
  id: ConversionTool
  title: string
  description: string
  icon: React.ComponentType<any>
  acceptedTypes: string[]
  maxFiles: number
  endpoint: string
}

const tools: ToolConfig[] = [
  {
    id: 'pdf-to-word',
    title: 'PDF to Word',
    description: 'Convert PDF documents to editable Word files',
    icon: FileText,
    acceptedTypes: ['.pdf'],
    maxFiles: 1,
    endpoint: '/api/convert/pdf-to-word'
  },
  {
    id: 'word-to-pdf',
    title: 'Word to PDF',
    description: 'Convert Word documents to PDF files',
    icon: RefreshCw,
    acceptedTypes: ['.doc', '.docx'],
    maxFiles: 1,
    endpoint: '/api/convert/word-to-pdf'
  },
  {
    id: 'merge-pdf',
    title: 'Merge PDFs',
    description: 'Combine multiple PDF files into one document',
    icon: Merge,
    acceptedTypes: ['.pdf'],
    maxFiles: 10,
    endpoint: '/api/convert/merge-pdf'
  },
  {
    id: 'image-to-pdf',
    title: 'Images to PDF',
    description: 'Convert JPG/PNG images to PDF documents',
    icon: Image,
    acceptedTypes: ['.jpg', '.jpeg', '.png'],
    maxFiles: 20,
    endpoint: '/api/convert/image-to-pdf'
  }
]

function App() {
  const [activeTool, setActiveTool] = useState<ConversionTool>('pdf-to-word')
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [conversionStatus, setConversionStatus] = useState<ConversionStatus>({
    status: 'idle',
    message: ''
  })
  const [uploadProgress, setUploadProgress] = useState(0)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const currentTool = tools.find(tool => tool.id === activeTool)!

  const validateFiles = (files: File[]): string | null => {
    if (files.length === 0) return 'Please select at least one file.'
    if (files.length > currentTool.maxFiles) {
      return `Maximum ${currentTool.maxFiles} file${currentTool.maxFiles > 1 ? 's' : ''} allowed.`
    }

    for (const file of files) {
      // Check file type
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
      if (!currentTool.acceptedTypes.includes(fileExtension)) {
        return `Invalid file type. Accepted types: ${currentTool.acceptedTypes.join(', ')}`
      }

      // Check file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        return `File "${file.name}" is too large. Maximum size is 10MB.`
      }
    }

    return null
  }

  const handleFileSelect = (files: File[]) => {
    const error = validateFiles(files)
    if (error) {
      setConversionStatus({
        status: 'error',
        message: error
      })
      return
    }

    setSelectedFiles(files)
    setConversionStatus({
      status: 'idle',
      message: ''
    })
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const files = Array.from(e.dataTransfer.files)
    handleFileSelect(files)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      handleFileSelect(Array.from(files))
    }
  }

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index)
    setSelectedFiles(newFiles)
    if (newFiles.length === 0) {
      setConversionStatus({ status: 'idle', message: '' })
    }
  }

  const convertFiles = async () => {
    if (selectedFiles.length === 0) return

    setConversionStatus({
      status: 'uploading',
      message: 'Uploading files...'
    })
    setUploadProgress(0)

    const formData = new FormData()
    
    if (currentTool.maxFiles === 1) {
      formData.append('file', selectedFiles[0])
    } else {
      selectedFiles.forEach((file, index) => {
        formData.append(`file_${index}`, file)
      })
      formData.append('file_count', selectedFiles.length.toString())
    }

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 200)

      const response = await fetch(currentTool.endpoint, {
        method: 'POST',
        body: formData
      })

      clearInterval(progressInterval)
      setUploadProgress(100)

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Conversion failed')
      }

      setConversionStatus({
        status: 'converting',
        message: 'Converting files...'
      })

      // Create download blob from response
      const blob = await response.blob()
      const downloadUrl = URL.createObjectURL(blob)
      
      setConversionStatus({
        status: 'success',
        message: 'Conversion completed successfully!',
        downloadUrl
      })

    } catch (error) {
      setConversionStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'An error occurred during conversion'
      })
    }
  }

  const downloadFile = () => {
    if (conversionStatus.downloadUrl && selectedFiles.length > 0) {
      const link = document.createElement('a')
      link.href = conversionStatus.downloadUrl
      
      // Generate appropriate filename based on tool
      let filename = ''
      const firstFile = selectedFiles[0]
      const baseName = firstFile.name.split('.')[0]
      
      switch (activeTool) {
        case 'pdf-to-word':
          filename = `${baseName}.docx`
          break
        case 'word-to-pdf':
          filename = `${baseName}.pdf`
          break
        case 'merge-pdf':
          filename = 'merged_document.pdf'
          break
        case 'image-to-pdf':
          filename = selectedFiles.length > 1 ? 'images_combined.pdf' : `${baseName}.pdf`
          break
      }
      
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }
  }

  const resetConverter = () => {
    setSelectedFiles([])
    setConversionStatus({
      status: 'idle',
      message: ''
    })
    setUploadProgress(0)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleToolChange = (toolId: string) => {
    setActiveTool(toolId as ConversionTool)
    resetConverter()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8 pt-8">
          <div className="flex items-center justify-center mb-4">
            <FileText className="h-8 w-8 text-primary mr-3" />
            <h1 className="text-3xl font-semibold text-gray-900">Document Converter</h1>
          </div>
          <p className="text-gray-600">
            Convert, merge, and transform your documents with ease
          </p>
        </div>

        {/* Tool Selector */}
        <Card className="shadow-lg border-0 bg-white/80 backdrop-blur-sm mb-6">
          <CardContent className="p-6">
            <Tabs value={activeTool} onValueChange={handleToolChange}>
              <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4">
                {tools.map((tool) => {
                  const Icon = tool.icon
                  return (
                    <TabsTrigger key={tool.id} value={tool.id} className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      <span className="hidden sm:inline">{tool.title}</span>
                    </TabsTrigger>
                  )
                })}
              </TabsList>

              {tools.map((tool) => (
                <TabsContent key={tool.id} value={tool.id} className="mt-6">
                  <div className="text-center mb-6">
                    <div className="flex items-center justify-center mb-3">
                      <tool.icon className="h-8 w-8 text-primary mr-3" />
                      <h2 className="text-2xl font-semibold text-gray-900">{tool.title}</h2>
                    </div>
                    <p className="text-gray-600">{tool.description}</p>
                  </div>

                  {/* File Upload Area */}
                  <div
                    className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
                      selectedFiles.length > 0
                        ? 'border-green-300 bg-green-50'
                        : 'border-gray-300 hover:border-primary hover:bg-blue-50'
                    }`}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept={tool.acceptedTypes.join(',')}
                      multiple={tool.maxFiles > 1}
                      onChange={handleFileInputChange}
                      className="hidden"
                    />

                    {selectedFiles.length > 0 ? (
                      <div className="space-y-4">
                        <CheckCircle className="h-12 w-12 text-green-500 mx-auto" />
                        <div className="space-y-2">
                          {selectedFiles.map((file, index) => (
                            <div key={index} className="flex items-center justify-between bg-white rounded-lg p-3 shadow-sm">
                              <div className="flex items-center space-x-3">
                                <FileText className="h-5 w-5 text-gray-400" />
                                <div className="text-left">
                                  <p className="font-medium text-gray-900 text-sm">{file.name}</p>
                                  <p className="text-xs text-gray-500">
                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                  </p>
                                </div>
                              </div>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeFile(index)}
                                className="text-red-500 hover:text-red-700 hover:bg-red-50"
                              >
                                ×
                              </Button>
                            </div>
                          ))}
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={resetConverter}
                          className="mt-2"
                        >
                          Choose Different Files
                        </Button>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        <Upload className="h-12 w-12 text-gray-400 mx-auto" />
                        <div>
                          <p className="text-lg font-medium text-gray-900 mb-2">
                            Drop your {tool.acceptedTypes.join(', ').replace(/\./g, '').toUpperCase()} file{tool.maxFiles > 1 ? 's' : ''} here
                          </p>
                          <p className="text-gray-500 mb-4">or</p>
                          <Button
                            onClick={() => fileInputRef.current?.click()}
                            className="bg-primary hover:bg-primary/90"
                          >
                            Browse Files
                          </Button>
                        </div>
                        <p className="text-xs text-gray-400">
                          {tool.maxFiles > 1 
                            ? `Supports up to ${tool.maxFiles} files, max 10MB each`
                            : 'Supports files up to 10MB'
                          }
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Conversion Progress */}
                  {conversionStatus.status === 'uploading' && (
                    <div className="mt-6 space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Uploading...</span>
                        <span className="text-gray-600">{uploadProgress}%</span>
                      </div>
                      <Progress value={uploadProgress} className="h-2" />
                    </div>
                  )}

                  {/* Status Messages */}
                  {conversionStatus.message && (
                    <div className="mt-6">
                      {conversionStatus.status === 'error' && (
                        <Alert className="border-red-200 bg-red-50">
                          <AlertCircle className="h-4 w-4 text-red-600" />
                          <AlertDescription className="text-red-800">
                            {conversionStatus.message}
                          </AlertDescription>
                        </Alert>
                      )}

                      {conversionStatus.status === 'converting' && (
                        <Alert className="border-blue-200 bg-blue-50">
                          <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />
                          <AlertDescription className="text-blue-800">
                            {conversionStatus.message}
                          </AlertDescription>
                        </Alert>
                      )}

                      {conversionStatus.status === 'success' && (
                        <Alert className="border-green-200 bg-green-50">
                          <CheckCircle className="h-4 w-4 text-green-600" />
                          <AlertDescription className="text-green-800">
                            {conversionStatus.message}
                          </AlertDescription>
                        </Alert>
                      )}
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="mt-8 flex gap-4">
                    {conversionStatus.status === 'success' ? (
                      <>
                        <Button
                          onClick={downloadFile}
                          className="flex-1 bg-accent hover:bg-accent/90"
                        >
                          <Download className="h-4 w-4 mr-2" />
                          Download File
                        </Button>
                        <Button
                          variant="outline"
                          onClick={resetConverter}
                          className="flex-1"
                        >
                          Convert More Files
                        </Button>
                      </>
                    ) : (
                      <Button
                        onClick={convertFiles}
                        disabled={selectedFiles.length === 0 || conversionStatus.status === 'uploading' || conversionStatus.status === 'converting'}
                        className="w-full bg-primary hover:bg-primary/90 disabled:opacity-50"
                      >
                        {conversionStatus.status === 'converting' ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Converting...
                          </>
                        ) : (
                          <>
                            <tool.icon className="h-4 w-4 mr-2" />
                            {tool.title === 'Merge PDFs' ? 'Merge Files' : 'Convert Files'}
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                </TabsContent>
              ))}
            </Tabs>
          </CardContent>
        </Card>

        {/* Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-center">
          {tools.map((tool) => {
            const Icon = tool.icon
            return (
              <div key={tool.id} className="p-4 bg-white/60 rounded-lg backdrop-blur-sm">
                <div className="h-12 w-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-3">
                  <Icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="font-medium text-gray-900 mb-1">{tool.title}</h3>
                <p className="text-sm text-gray-600">{tool.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default App
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileText, Shield, CheckCircle, AlertCircle, Download } from "lucide-react";
import { useState, useCallback, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";

const Dashboard = () => {
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const { toast } = useToast();
  const [stats, setStats] = useState<any>(null);
  const [loadingStats, setLoadingStats] = useState(false);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<{query: string, k: number, results: Array<{page: number, score: number, snippet: string}>} | null>(null);
  const [pdfReportBlob, setPdfReportBlob] = useState<Blob | null>(null);

  useEffect(() => {
    setLoadingStats(true);
    fetch("http://localhost:8000/analysis-stats")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch stats");
        return res.json();
      })
      .then((data) => {
        setStats(data);
        setStatsError(null);
      })
      .catch((err) => {
        setStatsError(err.message);
        setStats(null);
      })
      .finally(() => setLoadingStats(false));
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find(file => file.type === 'application/pdf');
    
    if (pdfFile) {
      setUploadedFile(pdfFile);
      toast({
        title: "File uploaded successfully",
        description: `${pdfFile.name} is ready for analysis`,
      });
    } else {
      toast({
        title: "Invalid file type",
        description: "Please upload a PDF file",
        variant: "destructive",
      });
    }
  }, [toast]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setUploadedFile(file);
      toast({
        title: "File uploaded successfully",
        description: `${file.name} is ready for analysis`,
      });
    }
  }, [toast]);

  const handleAnalyze = useCallback(async () => {
    if (!uploadedFile) return;

    setAnalyzing(true);
    try {
      // First, get the paragraph analysis (JSON)
      const formData = new FormData();
      formData.append('pdf', uploadedFile);
      formData.append('q', 'financial regulatory compliance analysis');
      formData.append('k', '5');

      const response = await fetch("http://localhost:8000/query-paragraphs", {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Analysis failed: ${response.statusText}`);
      }

      const results = await response.json();
      setAnalysisResults(results);
      
      // Then, generate the PDF report (but don't auto-download)
      const reportFormData = new FormData();
      reportFormData.append('user_document', uploadedFile);
      reportFormData.append('user_query', 'Generate a detailed compliance report with section-by-section regulatory mapping and specific citation analysis.');

      const reportResponse = await fetch("http://localhost:8000/generate-detailed-report/", {
        method: 'POST',
        body: reportFormData,
      });

      if (reportResponse.ok) {
        const blob = await reportResponse.blob();
        setPdfReportBlob(blob);
      }
      
      toast({
        title: "Analysis completed",
        description: `Found ${results.k} relevant sections. PDF report ready for download!`,
      });
    } catch (error) {
      toast({
        title: "Analysis failed", 
        description: error instanceof Error ? error.message : "Unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setAnalyzing(false);
    }
  }, [uploadedFile, toast]);

  const handleDownloadReport = useCallback(() => {
    if (!pdfReportBlob || !uploadedFile) return;

    const url = window.URL.createObjectURL(pdfReportBlob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `compliance_report_${uploadedFile.name}_${new Date().toISOString().slice(0, 10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    toast({
      title: "Report downloaded",
      description: "Your compliance report has been downloaded successfully.",
    });
  }, [pdfReportBlob, uploadedFile, toast]);

  const tips = [
    {
      icon: Shield,
      title: "Document Preparation",
      description: "Ensure all financial statements are complete and up-to-date"
    },
    {
      icon: CheckCircle,
      title: "Regular Audits",
      description: "Schedule quarterly compliance reviews to catch issues early"
    },
    {
      icon: AlertCircle,
      title: "Stay Updated",
      description: "Monitor regulatory changes and update policies accordingly"
    },
    {
      icon: FileText,
      title: "Documentation",
      description: "Maintain comprehensive records of all compliance activities"
    }
  ];

  return (
    <div className="min-h-screen animated-bg">
      <div className="container mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-12 animate-slide-up">
          <h1 className="text-4xl font-bold mb-4 text-white">
            FinReg
          </h1>
          <p className="text-white text-lg">
            Start Your Compliance Check
          </p>
        </div>

        {/* Upload Section */}
        <div className="max-w-4xl mx-auto mb-16">
          <Card className="glass border-0 p-8 animate-slide-up" style={{ animationDelay: '0.1s' }}>
            <div
              className={`upload-zone rounded-2xl p-12 text-center transition-all duration-300 ${
                dragOver ? 'border-primary/50 bg-primary/5' : ''
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="flex flex-col items-center space-y-4">
                <div className="bg-primary/10 p-6 rounded-full">
                  <Upload className="w-12 h-12 text-primary" />
                </div>
                
                {uploadedFile ? (
                  <div className="space-y-2">
                    <h3 className="text-xl font-semibold text-primary">File Ready for Analysis</h3>
                    <p className="text-muted-foreground">{uploadedFile.name}</p>
                    <Button 
                      variant="hero" 
                      className="glow-button mt-4"
                      onClick={handleAnalyze}
                      disabled={analyzing}
                    >
                      {analyzing ? "Analyzing..." : "Analyze Document"}
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <h3 className="text-xl font-semibold">Upload Financial Document</h3>
                    <p className="text-muted-foreground mb-4">
                      Drag and drop your PDF file here, or click to browse
                    </p>
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={handleFileInput}
                      className="hidden"
                      id="file-upload"
                    />
                    <label htmlFor="file-upload">
                      <Button variant="secondary" className="cursor-pointer" asChild>
                        <span>Choose File</span>
                      </Button>
                    </label>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* PDF Report Download Card */}
        {pdfReportBlob && (
          <div className="max-w-4xl mx-auto mb-16">
            <Card className="glass border-0 p-8 animate-slide-up" style={{ animationDelay: '0.1s' }}>
              <div className="text-center py-6">
                <div className="flex flex-col items-center space-y-4">
                  <div className="bg-green-500/10 p-6 rounded-full">
                    <FileText className="w-12 h-12 text-green-500" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-xl font-semibold text-green-500">Analysis Report Ready</h3>
                    <p className="text-muted-foreground">
                      Your comprehensive compliance analysis report has been generated successfully.
                    </p>
                    <p className="text-sm text-muted-foreground">
                      The report includes detailed regulatory mappings, compliance gaps, and recommendations.
                    </p>
                  </div>
                  <Button 
                    variant="default" 
                    className="bg-green-500 hover:bg-green-600 text-white"
                    onClick={handleDownloadReport}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download Report PDF
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Analysis Results */}
        {analysisResults && (
          <div className="max-w-4xl mx-auto mb-16">
            <Card className="glass border-0 p-8 animate-slide-up" style={{ animationDelay: '0.2s' }}>
              <div className="text-center py-8">
                <h3 className="text-xl font-semibold mb-4">Analysis Results</h3>
                <p className="text-muted-foreground mb-6">Found {analysisResults.k} relevant sections for: "{analysisResults.query}"</p>
                <div className="space-y-4 text-left">
                  {analysisResults.results.map((result, index) => (
                    <div key={index} className="bg-muted/10 rounded-lg p-4">
                      <div className="flex justify-between items-start mb-2">
                        <span className="font-semibold text-primary">Page {result.page || 'N/A'}</span>
                        <span className="text-sm text-muted-foreground">Score: {result.score}</span>
                      </div>
                      <p className="text-sm text-muted-foreground">{result.snippet}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Backend Stats Output */}
        <div className="max-w-4xl mx-auto mb-16">
          <Card className="glass border-0 p-8 animate-slide-up" style={{ animationDelay: '0.3s' }}>
            <div className="text-center py-8">
              <h3 className="text-xl font-semibold mb-4">Backend Analysis Stats</h3>
              {loadingStats ? (
                <p className="text-muted-foreground">Loading stats...</p>
              ) : statsError ? (
                <p className="text-red-500">Error: {statsError}</p>
              ) : stats ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-left">
                  {Object.entries(stats).map(([key, value]) => (
                    <div key={key} className="bg-muted/10 rounded-lg p-4">
                      <span className="font-semibold text-primary">{key.replace(/_/g, ' ')}:</span>
                      <span className="ml-2 text-muted-foreground">{String(value)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">No stats available.</p>
              )}
            </div>
          </Card>
        </div>

        {/* Tips Section */}
        <div className="max-w-6xl mx-auto pb-24">
          <h2 className="text-2xl font-bold text-center mb-8 animate-slide-up" style={{ animationDelay: '0.3s' }}>
            Tips to Avoid Compliance Issues
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {tips.map((tip, index) => (
              <Card
                key={index}
                className="glass glass-hover p-6 border-0 animate-slide-up"
                style={{ animationDelay: `${0.4 + index * 0.1}s` }}
              >
                <div className="text-center space-y-4">
                  <div className="bg-primary/10 p-4 rounded-full w-16 h-16 mx-auto flex items-center justify-center">
                    <tip.icon className="w-8 h-8 text-primary animate-glow-pulse" />
                  </div>
                  <h3 className="font-semibold">{tip.title}</h3>
                  <p className="text-sm text-muted-foreground">{tip.description}</p>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Trust Note Card */}
        <div className="fixed bottom-0 left-0 right-0 p-4">
          <Card className="glass border-0 bg-yellow-500/5 backdrop-blur-md border border-yellow-500/20">
            <div className="flex items-center justify-center py-3 px-6">
              <Shield className="w-5 h-5 text-yellow-400 mr-3 flex-shrink-0" />
              <div className="text-center">
                <p className="font-semibold text-white text-sm mb-1">
                  Your data, your control.
                </p>
                <p className="text-muted-foreground text-xs">
                  We never store sensitive documents. Files are processed securely and deleted after analysis.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
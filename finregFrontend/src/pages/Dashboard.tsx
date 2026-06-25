import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Upload, FileText, Shield, Check, AlertCircle, AlertTriangle, 
  Download, ArrowLeft, Loader2, ChevronDown, ChevronUp, Database, Info, ExternalLink, RefreshCw
} from "lucide-react";
import { useState, useCallback, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
import { useNavigate } from "react-router-dom";

// Steps in the compliance RAG pipeline
const STAGES = [
  { id: 'extract', label: 'Extracting Document Text' },
  { id: 'chunk', label: 'Generating Text Chunks' },
  { id: 'retrieve_reg', label: 'Retrieving Relevant Regulations' },
  { id: 'retrieve_company', label: 'Matching Company Excerpts' },
  { id: 'gemini', label: 'Performing Gemini Compliance Analysis' },
  { id: 'pdf', label: 'Generating PDF Audit Report' }
];

interface RegulationCitation {
  code: string;
  citation: string;
  category: string;
  title: string;
  requirement: string;
  deadline: string;
  frequency: string;
  source_url: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const Dashboard = () => {
  const [view, setView] = useState<'upload' | 'processing' | 'dashboard'>('upload');
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const { toast } = useToast();
  const navigate = useNavigate();

  // Citations directory at the bottom of upload view
  const [citations, setCitations] = useState<RegulationCitation[]>([]);
  const [loadingCitations, setLoadingCitations] = useState(false);

  // Analysis process states
  const [analyzing, setAnalyzing] = useState(false);
  const [stageStatuses, setStageStatuses] = useState<('pending' | 'loading' | 'done' | 'error')[]>(
    ['pending', 'pending', 'pending', 'pending', 'pending', 'pending']
  );

  // Analysis result states
  const [analysisResults, setAnalysisResults] = useState<any>(null);
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);
  const [expandedRAG, setExpandedRAG] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<'all' | 'non-compliant' | 'partially-compliant' | 'compliant'>('all');

  // Fetch compliance rules for display
  useEffect(() => {
    setLoadingCitations(true);
    fetch(`${API_BASE_URL}/regulatory-citations`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch citations");
        return res.json();
      })
      .then((data) => {
        if (data && data.items) {
          setCitations(data.items);
        }
      })
      .catch((err) => {
        console.error("Error fetching citations directory:", err);
      })
      .finally(() => setLoadingCitations(false));
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
        title: "Document Staged",
        description: `${pdfFile.name} loaded and ready for audit.`,
      });
    } else {
      toast({
        title: "Invalid file format",
        description: "Please upload a corporate PDF document.",
        variant: "destructive",
      });
    }
  }, [toast]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setUploadedFile(file);
      toast({
        title: "Document Staged",
        description: `${file.name} loaded and ready for audit.`,
      });
    }
  }, [toast]);

  const handleAnalyze = useCallback(async () => {
    if (!uploadedFile) return;

    // Start transition
    setView('processing');
    setAnalyzing(true);
    setStageStatuses(['loading', 'pending', 'pending', 'pending', 'pending', 'pending']);

    // Progress bar mock sequencer for first 4 steps
    let currentStage = 0;
    const progressTimer = setInterval(() => {
      setStageStatuses(prev => {
        const next = [...prev];
        next[currentStage] = 'done';
        if (currentStage + 1 < next.length) {
          next[currentStage + 1] = 'loading';
        }
        return next;
      });
      currentStage++;
      if (currentStage >= 4) {
        clearInterval(progressTimer);
      }
    }, 900);

    try {
      const formData = new FormData();
      formData.append('user_document', uploadedFile);

      const response = await fetch(`${API_BASE_URL}/analyze-compliance`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let errorMsg = `Audit failed: ${response.statusText}`;
        try {
          const errData = await response.json();
          if (errData && errData.error) {
            errorMsg = errData.error;
          }
        } catch (_) {}
        throw new Error(errorMsg);
      }

      const results = await response.json();
      
      // Stop the timer if it's still running
      clearInterval(progressTimer);

      // Finish stages
      setStageStatuses(['done', 'done', 'done', 'done', 'done', 'done']);
      setAnalysisResults(results);

      toast({
        title: "Audit Completed",
        description: "Indian Companies Act compliance checklist generated.",
      });

      // Quick visual transition delay
      setTimeout(() => {
        setView('dashboard');
        setAnalyzing(false);
      }, 600);

    } catch (error) {
      clearInterval(progressTimer);
      const errMsg = error instanceof Error ? error.message : "";
      
      setStageStatuses(prev => {
        const next = [...prev];
        const errMsgLower = errMsg.toLowerCase();
        
        // If it's a Gemini, 429, or Quota rate limit error, the prior RAG stages completed successfully.
        if (errMsgLower.includes('gemini') || errMsgLower.includes('quota') || errMsgLower.includes('429')) {
          next[0] = 'done'; // Text extraction
          next[1] = 'done'; // Chunk generation
          next[2] = 'done'; // Regulation retrieval
          next[3] = 'done'; // Company retrieval
          next[4] = 'error'; // Gemini Analysis
          next[5] = 'pending'; // PDF generation
        } else {
          const loadingIdx = next.findIndex(s => s === 'loading' || s === 'pending');
          if (loadingIdx !== -1) {
            next[loadingIdx] = 'error';
          }
        }
        return next;
      });
      setAnalyzing(false);
      
      toast({
        title: "Audit Processing Failed", 
        description: errMsg || "Internal backend processing error.",
        variant: "destructive",
      });
    }
  }, [uploadedFile, toast]);

  const handleDownloadReport = useCallback(() => {
    if (!analysisResults?.report_id) return;
    
    const downloadUrl = `${API_BASE_URL}/download-report/${analysisResults.report_id}`;
    
    // Create an anchor and trigger download
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = downloadUrl;
    a.download = `compliance_audit_report_${analysisResults.report_id.slice(0, 8)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    toast({
      title: "PDF Download Started",
      description: "Streaming direct cache representation of legal report.",
    });
  }, [analysisResults, toast]);

  const resetAudit = () => {
    setUploadedFile(null);
    setAnalysisResults(null);
    setView('upload');
    setStageStatuses(['pending', 'pending', 'pending', 'pending', 'pending', 'pending']);
    setExpandedFinding(null);
    setExpandedRAG(null);
    setActiveFilter('all');
  };

  const getConfidenceLevel = (score: number) => {
    if (score >= 90) return { label: "High Confidence", color: "bg-green-50 text-green-700 border-green-200" };
    if (score >= 70) return { label: "Medium Confidence", color: "bg-amber-50 text-amber-700 border-amber-200" };
    return { label: "Low Confidence", color: "bg-red-50 text-red-700 border-red-200" };
  };

  const getRiskLevelStyles = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'critical':
        return "bg-red-50 text-red-700 border-red-200";
      case 'high':
        return "bg-orange-50 text-orange-700 border-orange-200";
      case 'medium':
        return "bg-amber-50 text-amber-700 border-amber-200";
      case 'low':
      default:
        return "bg-green-50 text-green-700 border-green-200";
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Fully Compliant':
        return <Badge className="bg-green-100 text-green-800 hover:bg-green-200 border-0">Compliant</Badge>;
      case 'Partially Compliant':
        return <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-200 border-0">Partially Compliant</Badge>;
      case 'Non-Compliant':
      default:
        return <Badge className="bg-red-100 text-red-800 hover:bg-red-200 border-0">Non-Compliant</Badge>;
    }
  };

  // Filtering findings
  const filteredFindings = analysisResults?.findings.filter((f: any) => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'non-compliant') return f.status === 'Non-Compliant';
    if (activeFilter === 'partially-compliant') return f.status === 'Partially Compliant';
    if (activeFilter === 'compliant') return f.status === 'Fully Compliant';
    return true;
  }) || [];

  const toggleFinding = (code: string) => {
    setExpandedFinding(expandedFinding === code ? null : code);
  };

  const getEmptyStateContent = () => {
    switch (activeFilter) {
      case 'non-compliant':
        return {
          icon: <Check className="w-10 h-10 text-green-600 mx-auto" />,
          title: "All Clear! No Compliance Gaps",
          description: "Excellent! Your document does not contain any non-compliant sections for the assessed Indian Companies Act regulations.",
          bgClass: "bg-green-50/30 border-green-200"
        };
      case 'partially-compliant':
        return {
          icon: <Shield className="w-10 h-10 text-slate-400 mx-auto" />,
          title: "No Partially Compliant Sections",
          description: "There are no sections identified as partially compliant in the current document analysis.",
          bgClass: "bg-slate-50/50 border-slate-200"
        };
      case 'compliant':
        return {
          icon: <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />,
          title: "No Fully Compliant Sections",
          description: "No fully compliant sections were detected. Please review the gap analysis and remediation guidelines to achieve compliance.",
          bgClass: "bg-red-50/30 border-red-200"
        };
      case 'all':
      default:
        return {
          icon: <FileText className="w-10 h-10 text-slate-400 mx-auto" />,
          title: "No Findings Available",
          description: "No findings matched the active filters or no evaluations were performed.",
          bgClass: "bg-slate-50/50 border-slate-200"
        };
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-[#0f172a] font-sans antialiased pb-20">
      {/* Premium Top Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/85 backdrop-blur-md">
        <div className="container mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => navigate("/")}>
            <img src="/finreg-logo.svg" alt="FinReg" className="h-9" />
            <div className="h-6 w-px bg-slate-200" />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Corporate Compliance Suite</span>
          </div>
          {view === 'dashboard' && (
            <div className="flex items-center space-x-3">
              <Button variant="outline" size="sm" onClick={resetAudit} className="border-slate-200 h-9">
                <ArrowLeft className="w-4 h-4 mr-2" />
                New Audit
              </Button>
              <Button size="sm" onClick={handleDownloadReport} className="bg-slate-900 text-white hover:bg-slate-800 h-9 font-semibold">
                <Download className="w-4 h-4 mr-2" />
                Download Report PDF
              </Button>
            </div>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="container mx-auto px-6 mt-10 max-w-7xl">
        
        {/* VIEW 1: UPLOAD & SEED */}
        {view === 'upload' && (
          <div className="space-y-12 animate-slide-up">
            
            {/* Header Title */}
            <div className="max-w-4xl">
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
                Companies Act, 2013 Compliance Assessment
              </h1>
              <p className="mt-3 text-slate-500 text-base leading-relaxed">
                Upload annual reports, board reports, financial statements, or corporate governance documents. FinReg uses semantic Retrieval-Augmented Generation (RAG) to compare your document against the Companies Act, 2013 and generate an evidence-backed compliance assessment.
              </p>
            </div>

            {/* Drop Zone */}
            <Card className="border border-slate-200 shadow-sm bg-white overflow-hidden rounded-xl">
              <CardContent className="p-0">
                <div
                  className={`p-12 text-center transition-all duration-200 ${
                    dragOver ? 'bg-slate-50 border-slate-400' : 'bg-white'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <div className="flex flex-col items-center justify-center space-y-4">
                    <div className="bg-slate-100 p-5 rounded-full">
                      <Upload className="w-10 h-10 text-slate-600" />
                    </div>
                    
                    {uploadedFile ? (
                      <div className="space-y-4">
                        <div className="inline-flex items-center bg-slate-50 border border-slate-200 rounded-lg px-4 py-2">
                          <FileText className="w-5 h-5 text-slate-500 mr-2.5" />
                          <span className="text-sm font-semibold text-slate-700">{uploadedFile.name}</span>
                          <span className="text-xs text-slate-400 ml-2">({(uploadedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                        </div>
                        <p className="text-xs text-slate-400">Ready for statutory analysis.</p>
                        
                        <div className="flex justify-center space-x-3 mt-4">
                          <Button 
                            variant="outline" 
                            onClick={() => setUploadedFile(null)}
                            className="border-slate-200"
                          >
                            Remove
                          </Button>
                          <Button 
                            onClick={handleAnalyze}
                            className="bg-slate-900 text-white hover:bg-slate-800 px-8 font-semibold shadow-sm"
                          >
                            Run Compliance Audit
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2 max-w-md">
                        <h3 className="text-lg font-bold text-slate-900">Upload Financial or Corporate Document</h3>
                        <p className="text-sm text-slate-500 leading-relaxed">
                          Drag and drop your PDF report here, or <span className="font-semibold text-slate-800 underline cursor-pointer">browse file</span>.
                        </p>
                        <input
                          type="file"
                          accept=".pdf"
                          onChange={handleFileInput}
                          className="hidden"
                          id="file-upload"
                        />
                        <label htmlFor="file-upload" className="block mt-4">
                          <Button variant="outline" className="cursor-pointer border-slate-200" asChild>
                            <span>Select PDF File</span>
                          </Button>
                        </label>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Compliance Coverage Section */}
            <div className="space-y-5">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <h2 className="text-xl font-bold text-slate-900 flex items-center">
                  <Shield className="w-5 h-5 text-slate-700 mr-2" />
                  Compliance Framework Coverage
                </h2>
                <Badge variant="secondary" className="bg-slate-100 text-slate-600 font-semibold border-0">
                  Tracked Citations: {citations.length}
                </Badge>
              </div>

              {loadingCitations ? (
                <div className="flex items-center justify-center py-10">
                  <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
                  <span className="text-sm text-slate-500 ml-2">Loading coverage directory...</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {citations.map((cite) => (
                    <Card key={cite.code} className="border border-slate-200 bg-white hover:shadow-sm transition-all duration-150 rounded-xl">
                      <CardHeader className="pb-2">
                        <div className="flex justify-between items-start">
                          <Badge variant="outline" className="text-[10px] font-bold text-slate-600 uppercase border-slate-200">
                            {cite.frequency}
                          </Badge>
                          <span className="text-[10px] font-bold text-slate-400">{cite.code}</span>
                        </div>
                        <CardTitle className="text-base font-bold text-slate-900 mt-2 line-clamp-1">
                          {cite.citation.split(',')[0]}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pb-4">
                        <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">
                          {cite.requirement}
                        </p>
                      </CardContent>
                      <CardFooter className="border-t border-slate-100 pt-3 pb-3 flex justify-between items-center bg-slate-50/50 rounded-b-xl">
                        <span className="text-[10px] text-slate-400 font-medium">MCA Reference</span>
                        <a 
                          href={cite.source_url} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="text-[10px] text-slate-600 hover:text-slate-900 flex items-center font-semibold"
                        >
                          Official Portal
                          <ExternalLink className="w-2.5 h-2.5 ml-1" />
                        </a>
                      </CardFooter>
                    </Card>
                  ))}
                </div>
              )}
            </div>

            {/* Security Notice */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 flex items-start space-x-3 max-w-3xl mx-auto">
              <Info className="w-5 h-5 text-slate-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-slate-700">Audit Processing Transparency Notice</p>
                <p className="text-xs text-slate-500 leading-relaxed mt-1">
                  Compliance documents are processed purely in memory for extraction and ChromaDB indexing. Reports generated are cached in OS temporary folders. We do not store financial records permanently.
                </p>
              </div>
            </div>

          </div>
        )}

        {/* VIEW 2: PROGRESS CHECKMARKS */}
        {view === 'processing' && (
          <div className="max-w-2xl mx-auto py-12 animate-slide-up">
            <Card className="border border-slate-200 shadow-sm bg-white rounded-xl">
              <CardHeader className="text-center pb-6">
                <Loader2 className="w-10 h-10 animate-spin text-slate-800 mx-auto mb-4" />
                <CardTitle className="text-xl font-bold">Executing Statutory Compliance Diagnostics</CardTitle>
                <CardDescription>Evaluating company text against Indian Companies Act via RAG pipeline</CardDescription>
              </CardHeader>
              <CardContent className="px-10 pb-10 space-y-6">
                
                {/* Progress bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold text-slate-500">
                    <span>Audit Pipeline Stage</span>
                    <span>
                      {Math.round(
                        (stageStatuses.filter(s => s === 'done').length / STAGES.length) * 100
                      )}% Completed
                    </span>
                  </div>
                  <Progress 
                    value={
                      (stageStatuses.filter(s => s === 'done').length / STAGES.length) * 100
                    } 
                    className="h-2 bg-slate-100 indicator-slate-900"
                  />
                </div>

                {/* Checklist stages */}
                <div className="border border-slate-100 rounded-xl divide-y divide-slate-100 bg-slate-50/50">
                  {STAGES.map((stage, idx) => {
                    const status = stageStatuses[idx];
                    return (
                      <div key={stage.id} className="p-4 flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          {status === 'done' && (
                            <div className="bg-green-100 p-1.5 rounded-full">
                              <Check className="w-3.5 h-3.5 text-green-700" />
                            </div>
                          )}
                          {status === 'loading' && (
                            <div className="bg-blue-100 p-1.5 rounded-full animate-pulse">
                              <Loader2 className="w-3.5 h-3.5 text-blue-700 animate-spin" />
                            </div>
                          )}
                          {status === 'pending' && (
                            <div className="bg-slate-100 p-1.5 rounded-full">
                              <div className="w-3.5 h-3.5 rounded-full border border-slate-300 bg-white" />
                            </div>
                          )}
                          {status === 'error' && (
                            <div className="bg-red-100 p-1.5 rounded-full">
                              <AlertCircle className="w-3.5 h-3.5 text-red-700" />
                            </div>
                          )}
                          <span className={`text-sm ${
                            status === 'loading' ? 'font-bold text-slate-900' :
                            status === 'done' ? 'text-slate-700 font-medium' :
                            'text-slate-400'
                          }`}>
                            {stage.label}
                          </span>
                        </div>
                        <Badge variant="outline" className={`text-[10px] uppercase font-bold border-0 bg-transparent ${
                          status === 'loading' ? 'text-blue-700 animate-pulse' :
                          status === 'done' ? 'text-green-700' :
                          status === 'error' ? 'text-red-700' :
                          'text-slate-400'
                        }`}>
                          {status === 'done' ? 'Completed' : status === 'loading' ? 'Processing' : status === 'error' ? 'Error' : 'Pending'}
                        </Badge>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* VIEW 3: COMPLIANCE DASHBOARD */}
        {view === 'dashboard' && analysisResults && (
          <div className="space-y-8 animate-slide-up">
            
            {/* Top Row: Overall Score & Risk Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              
              {/* Card 1: Score */}
              <Card className="border border-slate-200 bg-white shadow-sm rounded-xl">
                <CardContent className="p-6 flex items-center space-x-5">
                  <div className="relative flex items-center justify-center flex-shrink-0">
                    <svg className="w-20 h-20 transform -rotate-90">
                      <circle cx="40" cy="40" r="34" stroke="#f1f5f9" strokeWidth="6" fill="transparent" />
                      <circle cx="40" cy="40" r="34" stroke="#0f172a" strokeWidth="6" fill="transparent"
                        strokeDasharray={213.6}
                        strokeDashoffset={213.6 - (213.6 * analysisResults.overall_score) / 100}
                        strokeLinecap="round"
                        className="transition-all duration-500"
                      />
                    </svg>
                    <span className="absolute text-base font-extrabold text-slate-900">{analysisResults.overall_score}%</span>
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Compliance Index</span>
                    <h3 className="text-xl font-black text-slate-900 mt-0.5">Audit Score</h3>
                    <p className="text-[10px] text-slate-400 mt-1"> assessed parameters mapped</p>
                  </div>
                </CardContent>
              </Card>

              {/* Card 2: Risk Profile */}
              <Card className="border border-slate-200 bg-white shadow-sm rounded-xl">
                <CardContent className="p-6">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Overall Risk Exposure</span>
                  <div className="flex items-center space-x-2.5 mt-2">
                    <div className={`w-3.5 h-3.5 rounded-full ${
                      analysisResults.overall_risk.toLowerCase() === 'critical' ? 'bg-red-500 animate-pulse' :
                      analysisResults.overall_risk.toLowerCase() === 'high' ? 'bg-orange-500' :
                      analysisResults.overall_risk.toLowerCase() === 'medium' ? 'bg-amber-500' :
                      'bg-green-500'
                    }`} />
                    <h3 className="text-2xl font-black text-slate-900">{analysisResults.overall_risk}</h3>
                  </div>
                  <Badge variant="outline" className={`mt-3 text-[10px] font-bold uppercase border ${getRiskLevelStyles(analysisResults.overall_risk)}`}>
                    Status: {analysisResults.overall_risk} Risk Profile
                  </Badge>
                </CardContent>
              </Card>

              {/* Card 3: Confidence Score */}
              <Card className="border border-slate-200 bg-white shadow-sm rounded-xl">
                <CardContent className="p-6">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">RAG & LLM Confidence</span>
                  <div className="flex items-baseline mt-1.5">
                    <h3 className="text-3xl font-black text-slate-900">{analysisResults.summary.average_confidence}%</h3>
                  </div>
                  <Badge variant="outline" className={`mt-3 text-[10px] font-bold uppercase border ${getConfidenceLevel(analysisResults.summary.average_confidence).color}`}>
                    {getConfidenceLevel(analysisResults.summary.average_confidence).label}
                  </Badge>
                </CardContent>
              </Card>

              {/* Card 4: Distribution */}
              <Card className="border border-slate-200 bg-white shadow-sm rounded-xl">
                <CardContent className="p-6">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Checks Summary</span>
                  <div className="grid grid-cols-3 gap-1.5 mt-3 text-center">
                    <div className="bg-green-50 border border-green-100 rounded-lg p-2">
                      <span className="block text-lg font-black text-green-700">{analysisResults.summary.compliant_count}</span>
                      <span className="text-[9px] font-bold text-green-600 uppercase">Met</span>
                    </div>
                    <div className="bg-amber-50 border border-amber-100 rounded-lg p-2">
                      <span className="block text-lg font-black text-amber-700">{analysisResults.summary.partially_compliant_count}</span>
                      <span className="text-[9px] font-bold text-amber-600 uppercase">Partial</span>
                    </div>
                    <div className="bg-red-50 border border-red-100 rounded-lg p-2">
                      <span className="block text-lg font-black text-red-700">{analysisResults.summary.non_compliant_count}</span>
                      <span className="text-[9px] font-bold text-red-600 uppercase">Gaps</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

            </div>

            {/* Executive Audit Summary Panel */}
            <Card className="border border-slate-200 bg-white shadow-sm rounded-xl">
              <CardHeader className="pb-2 border-b border-slate-100 bg-slate-50/50 rounded-t-xl">
                <CardTitle className="text-base font-bold text-slate-800 flex items-center">
                  <Shield className="w-4.5 h-4.5 text-slate-700 mr-2" />
                  Executive Audit Summary & Assessment Details
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <p className="text-slate-600 text-sm leading-relaxed whitespace-pre-line italic">
                  "{analysisResults.summary.executive_summary}"
                </p>
              </CardContent>
            </Card>

            {/* Findings Filter and Collapsible Checklist */}
            <div className="space-y-5">
              
              {/* Filter Tabs Header */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-200 pb-3 gap-3">
                <h2 className="text-xl font-bold text-slate-900">Detailed Compliance Assessment</h2>
                
                {/* Filter Tab Badges */}
                <div className="flex flex-wrap gap-1.5">
                  <Button 
                    variant={activeFilter === 'all' ? 'default' : 'outline'} 
                    size="sm" 
                    onClick={() => setActiveFilter('all')}
                    className={`h-8 text-xs px-3.5 border-slate-200 rounded-lg font-semibold ${
                      activeFilter === 'all' ? 'bg-slate-900 text-white hover:bg-slate-800' : ''
                    }`}
                  >
                    All Assessed ({analysisResults.findings.length})
                  </Button>
                  <Button 
                    variant={activeFilter === 'non-compliant' ? 'default' : 'outline'} 
                    size="sm" 
                    onClick={() => setActiveFilter('non-compliant')}
                    className={`h-8 text-xs px-3.5 border-slate-200 rounded-lg font-semibold ${
                      activeFilter === 'non-compliant' ? 'bg-red-900 text-white hover:bg-red-800 border-red-200' : 'text-red-700 hover:bg-red-50 hover:text-red-800'
                    }`}
                  >
                    Non-Compliant ({analysisResults.summary.non_compliant_count})
                  </Button>
                  <Button 
                    variant={activeFilter === 'partially-compliant' ? 'default' : 'outline'} 
                    size="sm" 
                    onClick={() => setActiveFilter('partially-compliant')}
                    className={`h-8 text-xs px-3.5 border-slate-200 rounded-lg font-semibold ${
                      activeFilter === 'partially-compliant' ? 'bg-amber-900 text-white hover:bg-amber-800 border-amber-200' : 'text-amber-700 hover:bg-amber-50 hover:text-amber-800'
                    }`}
                  >
                    Partially Compliant ({analysisResults.summary.partially_compliant_count})
                  </Button>
                  <Button 
                    variant={activeFilter === 'compliant' ? 'default' : 'outline'} 
                    size="sm" 
                    onClick={() => setActiveFilter('compliant')}
                    className={`h-8 text-xs px-3.5 border-slate-200 rounded-lg font-semibold ${
                      activeFilter === 'compliant' ? 'bg-green-900 text-white hover:bg-green-800 border-green-200' : 'text-green-700 hover:bg-green-50 hover:text-green-800'
                    }`}
                  >
                    Compliant ({analysisResults.summary.compliant_count})
                  </Button>
                </div>
              </div>

              {/* Collapsible Checklist Items */}
              {filteredFindings.length === 0 ? (
                (() => {
                  const content = getEmptyStateContent();
                  return (
                    <Card className={`border border-dashed p-12 text-center bg-white rounded-xl ${content.bgClass}`}>
                      <div className="flex flex-col items-center justify-center space-y-4 max-w-md mx-auto">
                        <div className="bg-white p-3 rounded-full shadow-sm border border-slate-100">
                          {content.icon}
                        </div>
                        <h3 className="text-base font-bold text-slate-900">{content.title}</h3>
                        <p className="text-sm text-slate-500 leading-relaxed">{content.description}</p>
                      </div>
                    </Card>
                  );
                })()
              ) : (
                <div className="space-y-4">
                  {filteredFindings.map((finding: any) => {
                    const isExpanded = expandedFinding === finding.requirement_code;
                    const confidenceMeta = getConfidenceLevel(finding.confidence_score);
                    
                    return (
                      <Card 
                        key={finding.requirement_code} 
                        className={`border transition-all duration-200 rounded-xl overflow-hidden bg-white ${
                          isExpanded ? 'border-slate-400 shadow-md' : 'border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {/* Heading Box */}
                        <div 
                          onClick={() => toggleFinding(finding.requirement_code)}
                          className="p-5 flex items-center justify-between cursor-pointer select-none hover:bg-slate-50/50"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
                            <span className="text-xs font-extrabold text-slate-400 w-16">{finding.requirement_code}</span>
                            <span className="text-sm font-bold text-slate-900">{finding.regulation_name}</span>
                            <div className="flex flex-wrap gap-1.5 mt-1 sm:mt-0">
                              {getStatusBadge(finding.status)}
                              <Badge variant="outline" className={`text-[9px] font-semibold border ${getRiskLevelStyles(finding.risk_level)}`}>
                                {finding.risk_level} Risk
                              </Badge>
                              <Badge variant="outline" className={`text-[9px] font-semibold border ${confidenceMeta.color}`}>
                                {finding.confidence_score}% Conf.
                              </Badge>
                            </div>
                          </div>
                          <div className="text-slate-400 ml-4 flex-shrink-0">
                            {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                          </div>
                        </div>

                        {/* Collapsed Expanded Contents */}
                        {isExpanded && (
                          <div className="border-t border-slate-100 p-6 bg-slate-50/20 space-y-6">
                            
                            {/* Key Gap & Remediation grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                              
                              {/* Left: Gap Analysis */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center">
                                  <AlertCircle className="w-3.5 h-3.5 text-slate-600 mr-1.5" />
                                  Statutory Gap Summary
                                </h4>
                                <div className={`p-4 rounded-xl border text-sm leading-relaxed ${
                                  finding.status === 'Fully Compliant' 
                                    ? 'bg-green-50/40 border-green-100 text-green-800' 
                                    : 'bg-red-50/40 border-red-100 text-red-800 font-medium'
                                }`}>
                                  {finding.gap_summary}
                                </div>
                              </div>

                              {/* Right: Remediation */}
                              <div className="space-y-2">
                                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center">
                                  <AlertTriangle className="w-3.5 h-3.5 text-slate-600 mr-1.5" />
                                  Actionable Recommendation
                                </h4>
                                <div className={`p-4 rounded-xl border text-sm leading-relaxed ${
                                  finding.status === 'Fully Compliant' 
                                    ? 'bg-slate-50 border-slate-200 text-slate-500' 
                                    : 'bg-blue-50/40 border-blue-100 text-blue-800 font-semibold'
                                }`}>
                                  {finding.recommendations || "No recommendations needed: Fully Compliant."}
                                </div>
                              </div>

                            </div>

                            {/* Section: Legal citations basis */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-3 border-t border-slate-100">
                              <div>
                                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Regulatory Citations</span>
                                <p className="text-sm font-semibold text-slate-700 mt-1">{finding.source_citations}</p>
                              </div>
                              <div>
                                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Document References</span>
                                <p className="text-sm font-semibold text-slate-700 mt-1">Page Reference: {finding.page_numbers}</p>
                              </div>
                            </div>

                            {/* Section: Full reasoning */}
                            <div className="space-y-2 pt-3 border-t border-slate-100">
                              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Detailed Compliance Evaluation & Rationale</h4>
                              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line bg-white p-4 rounded-xl border border-slate-100">
                                {finding.reasoning}
                              </p>
                            </div>

                            {/* Section: Evidence quotes */}
                            <div className="space-y-3 pt-3 border-t border-slate-100">
                              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">Direct Matching Evidence Quotes</h4>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-400 uppercase">Extract from Company Document</span>
                                  <div className="bg-slate-50 border-l-3 border-slate-700 p-3 rounded-r-lg text-xs leading-relaxed text-slate-600 font-mono italic animate-pulse-none">
                                    {finding.evidence_company ? `"${finding.evidence_company}"` : "No direct textual matching quotes indexed."}
                                  </div>
                                </div>
                                <div className="space-y-1.5">
                                  <span className="text-[10px] font-bold text-slate-400 uppercase">Regulatory Citation Standard</span>
                                  <div className="bg-slate-50 border-l-3 border-slate-400 p-3 rounded-r-lg text-xs leading-relaxed text-slate-600 font-mono italic animate-pulse-none">
                                    {finding.evidence_regulation ? `"${finding.evidence_regulation}"` : "No explicit matching regulation quote standard indexed."}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Section: RAG Transparency details */}
                            <div className="pt-4 border-t border-slate-100">
                              <div 
                                className="flex items-center space-x-2 text-xs font-bold text-slate-500 hover:text-slate-800 cursor-pointer select-none"
                                onClick={() => setExpandedRAG(expandedRAG === finding.requirement_code ? null : finding.requirement_code)}
                              >
                                <Database className="w-3.5 h-3.5" />
                                <span>RAG Retrieval Transparency Details</span>
                                <span>{expandedRAG === finding.requirement_code ? '(Hide)' : '(Show Matching Chunks)'}</span>
                              </div>
                              
                              {expandedRAG === finding.requirement_code && finding.rag_metadata && (
                                <div className="mt-4 p-4 rounded-xl border border-slate-200 bg-white space-y-4 animate-slide-up">
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    
                                    {/* Regulation matched chunks */}
                                    <div className="space-y-2">
                                      <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center">
                                        <Database className="w-3 h-3 mr-1 text-slate-500" />
                                        Retrieved Regulation Chunks (ChromaDB)
                                      </h5>
                                      {finding.rag_metadata.regulation_chunks && finding.rag_metadata.regulation_chunks.length > 0 ? (
                                        <div className="space-y-2 max-h-60 overflow-y-auto">
                                          {finding.rag_metadata.regulation_chunks.map((chunk: any, cidx: number) => (
                                            <div key={cidx} className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-[11px] space-y-1.5">
                                              <div className="flex justify-between text-[9px] font-bold text-slate-400">
                                                <span>Source: {chunk.source_filename || chunk.source || 'rules.pdf'} (Page {chunk.page_number})</span>
                                                <span className="text-slate-700">Similarity: {chunk.score ? `${Math.round(chunk.score * 100)}%` : 'N/A'}</span>
                                              </div>
                                              <p className="text-slate-600 leading-relaxed italic">"{chunk.text || chunk.snippet}"</p>
                                            </div>
                                          ))}
                                        </div>
                                      ) : (
                                        <p className="text-xs text-slate-400 italic">No matching regulation chunks in context limit.</p>
                                      )}
                                    </div>

                                    {/* Company matched chunks */}
                                    <div className="space-y-2">
                                      <h5 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center">
                                        <FileText className="w-3 h-3 mr-1 text-slate-500" />
                                        Extracted Company Document Excerpts
                                      </h5>
                                      {finding.rag_metadata.company_chunks && finding.rag_metadata.company_chunks.length > 0 ? (
                                        <div className="space-y-2 max-h-60 overflow-y-auto">
                                          {finding.rag_metadata.company_chunks.map((chunk: any, cidx: number) => (
                                            <div key={cidx} className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-[11px] space-y-1.5">
                                              <div className="flex justify-between text-[9px] font-bold text-slate-400">
                                                <span>Location: Company Document (Page {chunk.page_number || 'N/A'})</span>
                                              </div>
                                              <p className="text-slate-600 leading-relaxed italic">"{chunk.text || chunk.snippet}"</p>
                                            </div>
                                          ))}
                                        </div>
                                      ) : (
                                        <p className="text-xs text-slate-400 italic">No matching company document chunks in context limit.</p>
                                      )}
                                    </div>

                                  </div>
                                </div>
                              )}
                            </div>

                          </div>
                        )}
                      </Card>
                    );
                  })}
                </div>
              )}
            </div>

          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
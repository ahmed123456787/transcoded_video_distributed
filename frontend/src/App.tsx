import React, { useState, useRef, ChangeEvent } from "react";
import {
  UploadCloud,
  FileVideo,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import axios from "axios";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// --- Utility for Tailwind classes ---
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- Types ---
type UploadStatus =
  | "idle"
  | "getting_url"
  | "uploading"
  | "processing"
  | "success"
  | "error";

export default function VideoUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 1. Handle File Selection
  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      // Validation: Check if it's a video
      if (!selectedFile.type.startsWith("video/")) {
        setErrorMessage("Please upload a valid video file (MP4, MOV, etc).");
        return;
      }
      setFile(selectedFile);
      setErrorMessage("");
      setStatus("idle");
    }
  };

  // 2. Handle Drag & Drop
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selectedFile = e.dataTransfer.files[0];
      if (!selectedFile.type.startsWith("video/")) {
        setErrorMessage("Please upload a valid video file.");
        return;
      }
      setFile(selectedFile);
      setErrorMessage("");
      setStatus("idle");
    }
  };

  // 3. The Main Upload Logic (The "Netflix" Pattern)
  const handleUpload = async () => {
    if (!file) return;

    try {
      setStatus("getting_url");

      // STEP A: Ask API for Presigned URL
      // In a real app, replace with: const { data } = await axios.post('/api/upload-url', { filename: file.name });
      // We are mocking a 1-second delay here:
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const mockPresignedUrl = "https://httpbin.org/put"; // Free endpoint for testing PUT requests

      setStatus("uploading");

      // STEP B: Upload directly to S3 (Mocked here)
      await axios.put(mockPresignedUrl, file, {
        headers: {
          "Content-Type": file.type, // Important for S3
        },
        onUploadProgress: (progressEvent) => {
          const total = progressEvent.total || file.size;
          const current = progressEvent.loaded;
          const percentage = Math.round((current / total) * 100);
          setProgress(percentage);
        },
      });

      // STEP C: Notify Backend "I'm done" -> Start Processing
      setStatus("processing");
      // In real app: await axios.post('/api/upload-complete', { videoId: ... });

      // Mocking processing time (waiting for RabbitMQ/Worker)
      setTimeout(() => {
        setStatus("success");
      }, 2000);
    } catch (error) {
      console.error(error);
      setStatus("error");
      setErrorMessage("Upload failed. Please try again.");
    }
  };

  const removeFile = () => {
    setFile(null);
    setStatus("idle");
    setProgress(0);
    setErrorMessage("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100">
        {/* Header */}
        <div className="bg-slate-900 p-6 text-white">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <UploadCloud className="text-blue-400" />
            Upload Video
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Optimized for Netflix-style transcoding.
          </p>
        </div>

        <div className="p-8">
          {/* 1. DROP ZONE */}
          {!file && status === "idle" && (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-xl p-10 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-blue-50 hover:border-blue-400 transition-all group"
            >
              <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <UploadCloud size={32} />
              </div>
              <h3 className="font-semibold text-gray-700">
                Click or drag video
              </h3>
              <p className="text-sm text-gray-400 mt-2">
                MP4, MOV, MKV (Max 2GB)
              </p>
            </div>
          )}

          {/* 2. FILE PREVIEW CARD */}
          {file && (
            <div className="mb-6">
              <div className="flex items-center gap-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileVideo size={24} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
                {status === "idle" && (
                  <button
                    onClick={removeFile}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                  >
                    <X size={20} />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* 3. PROGRESS BAR */}
          {(status === "uploading" || status === "processing") && (
            <div className="mb-6">
              <div className="flex justify-between text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
                <span>
                  {status === "uploading"
                    ? "Uploading to S3..."
                    : "Transcoding..."}
                </span>
                <span>
                  {status === "uploading" ? `${progress}%` : "Please Wait"}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-300 ease-out",
                    status === "processing"
                      ? "w-full bg-indigo-500 animate-pulse"
                      : "bg-blue-600"
                  )}
                  style={{
                    width: status === "processing" ? "100%" : `${progress}%`,
                  }}
                />
              </div>
            </div>
          )}

          {/* 4. ERROR MESSAGE */}
          {errorMessage && (
            <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-3 text-sm">
              <AlertCircle size={18} />
              {errorMessage}
            </div>
          )}

          {/* 5. SUCCESS STATE */}
          {status === "success" && (
            <div className="mb-6 p-6 bg-green-50 rounded-xl border border-green-100 text-center animate-in fade-in zoom-in duration-300">
              <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 size={32} />
              </div>
              <h3 className="text-lg font-bold text-green-800">
                Ready to Stream!
              </h3>
              <p className="text-green-600 text-sm mt-1">
                Your video has been transcoded.
              </p>
            </div>
          )}

          {/* 6. ACTION BUTTONS */}
          <div className="mt-2">
            {status === "idle" && file && (
              <button
                onClick={handleUpload}
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5"
              >
                Start Upload
              </button>
            )}

            {status === "getting_url" && (
              <button
                disabled
                className="w-full py-3 px-4 bg-gray-100 text-gray-400 font-bold rounded-lg cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Loader2 className="animate-spin" size={18} /> Preparing
                Storage...
              </button>
            )}

            {status === "success" && (
              <button
                onClick={removeFile}
                className="w-full py-3 px-4 bg-white border border-gray-300 text-gray-700 font-bold rounded-lg hover:bg-gray-50 transition-colors"
              >
                Upload Another
              </button>
            )}
          </div>
        </div>

        {/* Hidden Input */}
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="video/*"
          className="hidden"
        />
      </div>
    </div>
  );
}

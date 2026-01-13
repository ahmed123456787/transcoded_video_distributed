import React, { useState, useRef, type ChangeEvent } from "react";
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

const API_BASE = "http://localhost:8000/api";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

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

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (!selectedFile.type.startsWith("video/")) {
        setErrorMessage("Please upload a valid video file (MP4, MOV, etc).");
        return;
      }
      setFile(selectedFile);
      setErrorMessage("");
      setStatus("idle");
    }
  };

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

  const handleUpload = async () => {
    if (!file) return;

    try {
      setStatus("getting_url");

      const { data } = await axios.post(`${API_BASE}/video-signedUrl`, {
        filename: file.name,
      });
      const { video_id, upload_url } = data;

      // URL is now correct from backend, no need to replace
      console.log("Upload URL:", upload_url);

      setStatus("uploading");

      // Step 2: Upload file to MinIO using presigned URL
      await axios.put(upload_url, file, {
        headers: { "Content-Type": file.type },
        onUploadProgress: (progressEvent) => {
          const total = progressEvent.total || file.size;
          const percentage = Math.round((progressEvent.loaded / total) * 100);
          setProgress(percentage);
        },
      });

      setStatus("processing");

      // Step 3: Start transcoding job
      await axios.post(`${API_BASE}/job-launch?video_id=${video_id}`);

      setStatus("success");
    } catch (error) {
      console.error("Upload error:", error);
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

          {file && (
            <div className="mb-6">
              <div className="flex items-center gap-4 bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-lg flex items-center justify-center shrink-0">
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

          {(status === "uploading" || status === "processing") && (
            <div className="mb-6">
              <div className="flex justify-between text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
                <span>
                  {status === "uploading"
                    ? "Uploading to MinIO..."
                    : "Starting Job..."}
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

          {errorMessage && (
            <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-3 text-sm">
              <AlertCircle size={18} />
              {errorMessage}
            </div>
          )}

          {status === "success" && (
            <div className="mb-6 p-6 bg-green-50 rounded-xl border border-green-100 text-center">
              <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 size={32} />
              </div>
              <h3 className="text-lg font-bold text-green-800">Job Started!</h3>
              <p className="text-green-600 text-sm mt-1">
                Your video is being transcoded.
              </p>
            </div>
          )}

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
                <Loader2 className="animate-spin" size={18} /> Getting URL...
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

import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, 
  User, 
  Car, 
  Plus, 
  X, 
  Trash2, 
  CheckCircle2, 
  Camera, 
  Upload, 
  Eye, 
  AlertTriangle 
} from 'lucide-react';

const getApiBaseUrl = () => {
  const envUrl = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().startsWith('http') && !envUrl.includes('onrender.com')) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined' && window.location && window.location.origin) {
    return window.location.origin;
  }
  return 'http://localhost:8000';
};
const API_BASE_URL = getApiBaseUrl();

// Helper utility to read and compress File objects as scaled JPEG Data URLs
const readFileAndCompress = (file, maxWidth = 800, quality = 0.75) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = (err) => reject(err);
    reader.onload = (e) => {
      const img = new Image();
      img.onerror = (err) => reject(err);
      img.onload = () => {
        let width = img.width;
        let height = img.height;

        if (width > maxWidth || height > maxWidth) {
          if (width > height) {
            height = Math.round((height * maxWidth) / width);
            width = maxWidth;
          } else {
            width = Math.round((width * maxWidth) / height);
            height = maxWidth;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height);
          const compressedDataUrl = canvas.toDataURL('image/jpeg', quality);
          resolve(compressedDataUrl);
        } else {
          reject(new Error('Failed to get 2D context'));
        }
      };
      img.src = e.target?.result;
    };
    reader.readAsDataURL(file);
  });
};

export default function WatchlistModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('faces');
  const [suspectPlates, setSuspectPlates] = useState([]);
  const [suspectFaces, setSuspectFaces] = useState([]);
  const [loading, setLoading] = useState(false);

  // Plate inputs
  const [newPlate, setNewPlate] = useState('');
  const [plateReason, setPlateReason] = useState('');
  const [platePriority, setPlatePriority] = useState('RED');

  // Face inputs & multi-photo selection
  const [newFaceName, setNewFaceName] = useState('');
  const [faceNotes, setFaceNotes] = useState('');
  const [facePriority, setFacePriority] = useState('RED');
  const [newFacePhotos, setNewFacePhotos] = useState([]);
  const [previewPhotoUrl, setPreviewPhotoUrl] = useState(null);

  const fileInputRef = useRef(null);
  const appendFileInputRef = useRef(null);
  const [targetAppendIdx, setTargetAppendIdx] = useState(null);

  const fetchWatchlist = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/watchlist`);
      if (res.ok) {
        const data = await res.json();
        setSuspectPlates(data.suspect_plates || []);
        setSuspectFaces(data.suspect_faces || []);
      }
    } catch (err) {
      console.error('Failed to load watchlist:', err);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchWatchlist();
    }
  }, [isOpen]);

  const saveWatchlist = async (updatedPlates, updatedFaces) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          suspect_plates: updatedPlates,
          suspect_faces: updatedFaces,
        }),
      });

      if (res.ok) {
        setSuspectPlates(updatedPlates);
        setSuspectFaces(updatedFaces);
      }
    } catch (err) {
      console.error('Failed to save watchlist:', err);
    } finally {
      setLoading(false);
    }
  };

  // Safe Guard: Conditional rendering check placed AFTER all hooks
  if (!isOpen) return null;

  // -------------------------------------------------------------------------
  // BOLO Plate Handlers
  // -------------------------------------------------------------------------
  const handleAddPlate = (e) => {
    e.preventDefault();
    if (!newPlate.trim()) return;
    const updated = [
      ...suspectPlates,
      {
        plate: newPlate.trim().toUpperCase(),
        reason: plateReason.trim() || 'Flagged for Border Inspection',
        priority: platePriority,
      },
    ];
    saveWatchlist(updated, suspectFaces);
    setNewPlate('');
    setPlateReason('');
  };

  const handleDeletePlate = (idx) => {
    const updated = suspectPlates.filter((_, i) => i !== idx);
    saveWatchlist(updated, suspectFaces);
  };

  // -------------------------------------------------------------------------
  // Multi-Photo FRS Enrolment Handlers
  // -------------------------------------------------------------------------
  const handlePhotosSelected = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    try {
      const compressedResults = await Promise.all(
        files.map((file) => readFileAndCompress(file))
      );
      setNewFacePhotos((prev) => [...prev, ...compressedResults.filter(Boolean)]);
    } catch (err) {
      console.error('Failed to process reference images:', err);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleRemoveNewPhoto = (idx) => {
    setNewFacePhotos((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleAddFace = async (e) => {
    e.preventDefault();
    if (!newFaceName.trim()) return;

    setLoading(true);
    const sid = `SUSP_${Date.now().toString().slice(-4)}`;
    const uploadedUrls = [];

    try {
      for (let i = 0; i < newFacePhotos.length; i++) {
        const photoData = newFacePhotos[i];
        const res = await fetch(`${API_BASE_URL}/api/watchlist/upload_photo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            person_id: sid,
            image_data: photoData,
          }),
        });
        if (res.ok) {
          const out = await res.json();
          if (out.url) uploadedUrls.push(out.url);
        }
      }

      const newSuspect = {
        id: sid,
        name: newFaceName.trim(),
        priority: facePriority,
        notes: faceNotes.trim() || 'Cross-border watchlist record',
        photos: uploadedUrls,
        created_at: new Date().toISOString(),
      };

      const updated = [...suspectFaces, newSuspect];
      await saveWatchlist(suspectPlates, updated);

      setNewFaceName('');
      setFaceNotes('');
      setNewFacePhotos([]);
    } catch (err) {
      console.error('Error adding suspect with photos:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerAppendPhoto = (idx) => {
    setTargetAppendIdx(idx);
    if (appendFileInputRef.current) {
      appendFileInputRef.current.click();
    }
  };

  const handleAppendPhotoFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file || targetAppendIdx === null) return;

    setLoading(true);
    try {
      const compressedDataUrl = await readFileAndCompress(file);
      if (!compressedDataUrl) return;

      const targetSuspect = suspectFaces[targetAppendIdx];
      const res = await fetch(`${API_BASE_URL}/api/watchlist/upload_photo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person_id: targetSuspect.id || 'SUSP',
          image_data: compressedDataUrl,
        }),
      });

      if (res.ok) {
        const out = await res.json();
        if (out.url) {
          const updated = [...suspectFaces];
          const currentPhotos = updated[targetAppendIdx].photos || [];
          updated[targetAppendIdx] = {
            ...updated[targetAppendIdx],
            photos: [...currentPhotos, out.url],
          };
          await saveWatchlist(suspectPlates, updated);
        }
      }
    } catch (err) {
      console.error('Failed to append photo:', err);
    } finally {
      setTargetAppendIdx(null);
      if (appendFileInputRef.current) appendFileInputRef.current.value = '';
      setLoading(false);
    }
  };

  const handleDeletePhotoFromSuspect = (suspectIdx, photoIdx) => {
    const updated = [...suspectFaces];
    const photos = (updated[suspectIdx].photos || []).filter((_, i) => i !== photoIdx);
    updated[suspectIdx] = { ...updated[suspectIdx], photos };
    saveWatchlist(suspectPlates, updated);
  };

  const handleDeleteFace = (idx) => {
    const updated = suspectFaces.filter((_, i) => i !== idx);
    saveWatchlist(suspectPlates, updated);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="bg-slate-950 px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="bg-red-600/20 border border-red-500 p-2 rounded-lg text-red-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
                Threat Watchlist & FRS Enrolment (Multi-Photo)
              </h3>
              <p className="text-[11px] text-slate-400">
                Enroll suspect profiles with multiple reference photos for high-confidence camera identification
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-slate-800 bg-slate-950/50">
          <button
            onClick={() => setActiveTab('faces')}
            className={`flex-1 py-2.5 text-xs font-bold flex items-center justify-center gap-2 border-b-2 transition ${
              activeTab === 'faces'
                ? 'border-cyan-500 text-cyan-400 bg-cyan-950/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <User className="w-4 h-4" /> FRS Suspect Faces ({suspectFaces.length})
          </button>
          <button
            onClick={() => setActiveTab('plates')}
            className={`flex-1 py-2.5 text-xs font-bold flex items-center justify-center gap-2 border-b-2 transition ${
              activeTab === 'plates'
                ? 'border-yellow-500 text-yellow-400 bg-yellow-950/10'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Car className="w-4 h-4" /> BOLO Vehicle Plates ({suspectPlates.length})
          </button>
        </div>

        {/* Content */}
        <div className="p-5 flex-1 overflow-y-auto">
          {activeTab === 'faces' ? (
            <div className="flex flex-col gap-5">
              {/* Add Face Form */}
              <form onSubmit={handleAddFace} className="bg-slate-950/80 p-4 rounded-xl border border-slate-800 flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-cyan-400 uppercase tracking-wide flex items-center gap-1.5">
                    <Camera className="w-3.5 h-3.5" /> Enroll New Person of Interest
                  </span>
                  <span className="text-[10px] text-slate-500">
                    Add frontal & angled photos for maximum recognition accuracy
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
                  <input
                    type="text"
                    placeholder="Full Name / Alias (e.g. Tariq M.)"
                    value={newFaceName}
                    onChange={(e) => setNewFaceName(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-cyan-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Notes / Threat Brief (e.g. Infiltrator)"
                    value={faceNotes}
                    onChange={(e) => setFaceNotes(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                  <select
                    value={facePriority}
                    onChange={(e) => setFacePriority(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
                  >
                    <option value="RED">RED (Wanted / High Threat)</option>
                    <option value="AMBER">AMBER (Person of Interest)</option>
                    <option value="BLUE">BLUE (Authorized Personnel)</option>
                  </select>
                </div>

                {/* Multi-Photo Picker */}
                <div className="border border-dashed border-slate-800 hover:border-cyan-500/50 rounded-xl p-3 bg-slate-900/40 transition">
                  <input
                    type="file"
                    ref={fileInputRef}
                    multiple
                    accept="image/*"
                    className="hidden"
                    onChange={handlePhotosSelected}
                  />

                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="bg-slate-800 hover:bg-slate-700 text-cyan-300 px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition border border-slate-700"
                      >
                        <Upload className="w-3.5 h-3.5 text-cyan-400" />
                        Select Reference Photos ({newFacePhotos.length} selected)
                      </button>
                      <span className="text-[11px] text-slate-400">
                        Upload front, side, or angled images
                      </span>
                    </div>

                    <button
                      type="submit"
                      disabled={loading || !newFaceName.trim()}
                      className="bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-bold px-4 py-1.5 rounded-lg text-xs transition flex items-center gap-1.5 shadow-lg shadow-cyan-950"
                    >
                      <Plus className="w-4 h-4" />
                      {loading ? 'Enrolling...' : 'Enroll Suspect into FRS'}
                    </button>
                  </div>

                  {/* Selected Photos Preview Strip */}
                  {newFacePhotos.length > 0 && (
                    <div className="flex gap-2.5 mt-3 overflow-x-auto pb-1">
                      {newFacePhotos.map((photoSrc, pIdx) => (
                        <div key={pIdx} className="relative group w-16 h-16 rounded-lg overflow-hidden border border-cyan-500/40 bg-slate-950 flex-shrink-0">
                          <img
                            src={photoSrc}
                            alt={`Preview ${pIdx + 1}`}
                            className="w-full h-full object-cover"
                          />
                          <span className="absolute bottom-0 inset-x-0 bg-black/70 text-[9px] text-center text-cyan-300 font-mono py-0.5">
                            Angle #{pIdx + 1}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleRemoveNewPhoto(pIdx)}
                            className="absolute top-0.5 right-0.5 bg-rose-600/90 text-white rounded p-0.5 opacity-90 hover:opacity-100"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </form>

              {/* Enrolled Suspects Profile Cards */}
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                  <span className="font-semibold uppercase tracking-wider text-[11px]">
                    Active Suspect Intelligence Records ({suspectFaces.length})
                  </span>
                  <span className="text-[11px] text-slate-500">
                    Matches are cross-referenced across all enrolled photo angles
                  </span>
                </div>

                {suspectFaces.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-500 border border-slate-800 rounded-xl bg-slate-950/30">
                    No suspect profiles enrolled in FRS. Add a person with reference photos above.
                  </div>
                ) : (
                  suspectFaces.map((f, idx) => {
                    const photos = f.photos || [];
                    return (
                      <div
                        key={idx}
                        className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-xl flex flex-col gap-3 hover:border-slate-700 transition"
                      >
                        {/* Profile Top Row */}
                        <div className="flex items-center justify-between flex-wrap gap-2 text-xs">
                          <div className="flex items-center gap-2.5">
                            <span className="font-bold text-slate-100 text-sm flex items-center gap-1.5">
                              <User className="w-4 h-4 text-cyan-400" />
                              {f.name}
                            </span>
                            <span className="font-mono text-[10px] text-slate-400 bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded">
                              {f.id || `ID-${idx + 1}`}
                            </span>
                            <span
                              className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border ${
                                f.priority === 'RED'
                                  ? 'bg-rose-950 text-rose-300 border-rose-700'
                                  : f.priority === 'AMBER'
                                  ? 'bg-amber-950 text-amber-300 border-amber-700'
                                  : 'bg-blue-950 text-blue-300 border-blue-700'
                              }`}
                            >
                              {f.priority || 'RED'}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => handleTriggerAppendPhoto(idx)}
                              className="bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-slate-700 px-2 py-1 rounded text-[11px] flex items-center gap-1 transition"
                              title="Upload additional angle photo for this suspect"
                            >
                              <Camera className="w-3 h-3" /> + Add Angle
                            </button>
                            <button
                              onClick={() => handleDeleteFace(idx)}
                              className="text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-slate-900 transition"
                              title="Delete Suspect Profile"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>

                        {/* Notes */}
                        {f.notes && (
                          <div className="text-[11px] text-slate-400 bg-slate-900/50 px-2.5 py-1 rounded-lg border border-slate-800/60">
                            {f.notes}
                          </div>
                        )}

                        {/* Photo Gallery Strip */}
                        <div className="flex items-center gap-2.5 flex-wrap">
                          {photos.length === 0 ? (
                            <div className="flex items-center gap-1.5 text-[11px] text-amber-400/80 bg-amber-950/20 border border-amber-900/40 px-2.5 py-1 rounded-lg">
                              <AlertTriangle className="w-3.5 h-3.5" />
                              No photos enrolled yet. Click "+ Add Angle" to upload reference photos for camera matching.
                            </div>
                          ) : (
                            photos.map((photoUrl, pIdx) => (
                              <div
                                key={pIdx}
                                className="relative group w-14 h-14 rounded-lg overflow-hidden border border-slate-700 hover:border-cyan-400 bg-slate-900 transition"
                              >
                                <img
                                  src={photoUrl}
                                  alt={`${f.name} angle ${pIdx + 1}`}
                                  className="w-full h-full object-cover cursor-pointer"
                                  onClick={() => setPreviewPhotoUrl(photoUrl)}
                                />
                                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 flex items-center justify-center gap-1 transition">
                                  <button
                                    type="button"
                                    onClick={() => setPreviewPhotoUrl(photoUrl)}
                                    className="p-1 text-slate-200 hover:text-white"
                                    title="View Full Photo"
                                  >
                                    <Eye className="w-3 h-3" />
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleDeletePhotoFromSuspect(idx, pIdx)}
                                    className="p-1 text-rose-400 hover:text-rose-300"
                                    title="Remove Photo"
                                  >
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                </div>
                              </div>
                            ))
                          )}

                          {photos.length > 0 && (
                            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/40 px-2 py-0.5 rounded-full">
                              ✓ {photos.length} {photos.length === 1 ? 'Angle Enrolled' : 'Angles Enrolled (Multi-Photo Active)'}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {/* Add Plate Form */}
              <form onSubmit={handleAddPlate} className="bg-slate-950/70 p-3 rounded-xl border border-slate-800 flex gap-2 items-center flex-wrap text-xs">
                <input
                  type="text"
                  placeholder="Plate (e.g., JK02C9988)"
                  value={newPlate}
                  onChange={(e) => setNewPlate(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 font-mono text-yellow-300 w-32 focus:outline-none"
                  required
                />
                <input
                  type="text"
                  placeholder="Reason / Intelligence brief..."
                  value={plateReason}
                  onChange={(e) => setPlateReason(e.target.value)}
                  className="flex-1 min-w-[140px] bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none"
                />
                <select
                  value={platePriority}
                  onChange={(e) => setPlatePriority(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 font-mono"
                >
                  <option value="RED">RED (Critical / Suspect)</option>
                  <option value="AMBER">AMBER (Warning / Flagged)</option>
                  <option value="BLUE">BLUE (Authorized / Friendly)</option>
                </select>
                <button
                  type="submit"
                  disabled={loading}
                  className="bg-yellow-600 hover:bg-yellow-500 text-slate-950 font-bold px-3 py-1.5 rounded-lg transition flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </form>

              {/* Plates List */}
              <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/30">
                {suspectPlates.length === 0 ? (
                  <div className="p-4 text-center text-xs text-slate-500">No vehicle plates in watchlist.</div>
                ) : (
                  suspectPlates.map((p, idx) => (
                    <div key={idx} className="p-3 flex items-center justify-between text-xs hover:bg-slate-800/30">
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold bg-yellow-950 text-yellow-300 border border-yellow-700 px-2 py-0.5 rounded">
                          {p.plate}
                        </span>
                        <span className="text-slate-300">{p.reason}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                          p.priority === 'RED'
                            ? 'bg-rose-950 text-rose-300 border-rose-700'
                            : p.priority === 'BLUE'
                            ? 'bg-blue-950 text-blue-300 border-blue-700'
                            : 'bg-amber-950 text-amber-300 border-amber-700'
                        }`}>
                          {p.priority}
                        </span>
                        <button
                          onClick={() => handleDeletePlate(idx)}
                          className="text-slate-500 hover:text-rose-400 p-1 rounded"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Hidden File Input for Appending Photo */}
        <input
          type="file"
          ref={appendFileInputRef}
          accept="image/*"
          className="hidden"
          onChange={handleAppendPhotoFile}
        />

        {/* Photo Fullscreen Preview Modal */}
        {previewPhotoUrl && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 p-4">
            <div className="relative max-w-lg w-full bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-2xl p-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                <span className="text-xs font-bold text-slate-200">FRS Enrolled Photo Preview</span>
                <button
                  onClick={() => setPreviewPhotoUrl(null)}
                  className="text-slate-400 hover:text-white p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <img
                src={previewPhotoUrl}
                alt="Enrolled Reference"
                className="w-full max-h-[70vh] object-contain rounded-lg bg-black"
              />
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="bg-slate-950 px-5 py-3 border-t border-slate-800 flex justify-between items-center text-xs">
          <span className="text-slate-500 text-[11px] flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            Active watchlist updates sync automatically with camera detection pipeline
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 font-semibold bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

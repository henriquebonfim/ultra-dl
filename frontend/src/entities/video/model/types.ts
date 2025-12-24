/**
 * Video entity types
 * Represents video metadata and format information from YouTube
 */

export interface VideoInfo {
  id: string;
  title: string;
  uploader: string;
  duration: number;
  thumbnail: string;
}

export interface VideoFormat {
  format_id: string;
  ext: string;
  resolution: string;
  height: number;
  note: string;
  filesize: number | null;
  vcodec: string;
  acodec: string;
}

export interface VideoMetadata {
  meta: VideoInfo;
  formats: VideoFormat[];
}

export interface VideoResolutionsResponse extends VideoMetadata {}

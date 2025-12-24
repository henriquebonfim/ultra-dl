interface AdBannerProps {
  className?: string;
}

export const AdBanner = ({ className = "" }: AdBannerProps) => {
  return (
    <div
      className={`w-full max-w-3xl mx-auto ${className}`}
      role="complementary"
      aria-label="Advertisement"
    >
      <div className="relative border border-border/50 rounded-xl bg-card/30 p-6 flex items-center justify-center min-h-[90px]">
        <span className="text-muted-foreground text-sm">
          Ad Space 728×90
        </span>
      </div>
    </div>
  );
};

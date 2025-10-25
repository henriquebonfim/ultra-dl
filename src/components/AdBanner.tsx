import { motion } from "framer-motion";

interface AdBannerProps {
  position: "top" | "bottom";
  size?: string;
}

export const AdBanner = ({ position, size = "728x90" }: AdBannerProps) => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5, delay: position === "bottom" ? 0.3 : 0 }}
      className={`w-full flex items-center justify-center ${
        position === "top" ? "mb-8" : "mt-8"
      }`}
    >
      <div className="bg-muted/30 border border-border rounded-lg p-4 flex items-center justify-center min-h-[90px] w-full max-w-[728px]">
        <span className="text-muted-foreground text-sm">Ad Space {size}</span>
      </div>
    </motion.div>
  );
};

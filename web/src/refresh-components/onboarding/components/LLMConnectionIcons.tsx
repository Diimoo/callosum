import React, { memo } from "react";
import { SvgArrowExchange, SvgCallosumLogo } from "@opal/icons";
type LLMConnectionIconsProps = {
  icon: React.ReactNode;
};

const LLMConnectionIconsInner = ({ icon }: LLMConnectionIconsProps) => {
  return (
    <div className="flex items-center gap-1">
      <div className="w-7 h-7 flex items-center justify-center">{icon}</div>
      <div className="w-4 h-4 flex items-center justify-center">
        <SvgArrowExchange className="w-3 h-3 stroke-text-04" />
      </div>
      <div className="w-7 h-7 flex items-center justify-center">
        <SvgCallosumLogo width={24} height={24} className="fill-text-04" />
      </div>
    </div>
  );
};

const LLMConnectionIcons = memo(LLMConnectionIconsInner);
export default LLMConnectionIcons;

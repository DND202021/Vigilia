/**
 * MessagesPage
 * Communication Hub page with channels and messaging
 */

import { ChatPanel } from '../components/chat';

export function MessagesPage() {
  return (
    <div className="h-[calc(100vh-4rem)]">
      <ChatPanel />
    </div>
  );
}

export default MessagesPage;

export const metadata = {
  title: 'Contractor Onboarding',
  description: 'Christmas Light Contractor Registration'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}


<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:sf="http://soap.sforce.com/2006/04/metadata" xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xslt="http://xml.apache.org/xslt" xmlns:xalan="http://xml.apache.org/xalan" exclude-result-prefixes="sf">
  <xsl:output method="xml" indent="yes" standalone="yes" xsl:indent-amount="4" xslt:indent-amount="4" xalan:indent-amount="4" />

  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()" />
    </xsl:copy>
  </xsl:template>

  <xsl:template match="sf:Package">
    <xsl:copy>
      <xsl:apply-templates select="@*" />
      <xsl:apply-templates select="sf:fullName" />
      <xsl:apply-templates select="sf:postInstallClass" />
      <xsl:apply-templates select="sf:types">    
        <xsl:sort select="sf:name"/>
      </xsl:apply-templates>
      <xsl:apply-templates select="sf:uninstallClass" />
      <xsl:apply-templates select="sf:version" />
    </xsl:copy>
  </xsl:template>

</xsl:stylesheet>
